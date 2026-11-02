"""视频路由：上传（含标题/描述审核）/ 列表 / 详情"""
import json
import os
import shutil
import struct
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from db import db_cursor, BASE_DIR
from auth import get_current_user
from audit.pipeline import audit_text, enqueue_review
from models import STATUS_VIDEO_APPROVED, STATUS_VIDEO_PENDING, SOURCE_VIDEO_COMMENT

router = APIRouter(prefix="/api/videos", tags=["videos"])

STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "videos")          # 视频落盘 static/videos
COVER_DIR = os.path.join(STATIC_DIR, "uploads", "covers")  # 封面落盘 static/uploads/covers
ALLOWED_EXT = {".mp4", ".webm", ".mov", ".mkv", ".avi"}
ALLOWED_COVER_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIZE = 200 * 1024 * 1024  # 200MB
MAX_COVER_SIZE = 10 * 1024 * 1024  # 封面 10MB
THUMB_DIR = os.path.join(COVER_DIR, "thumbs")  # 封面缩略图目录 static/uploads/covers/thumbs
THUMB_WIDTH = 360  # 缩略图宽度上限（等比缩放）
# MIME 白名单（批次三：上传内容类型二次校验，防止伪装扩展名）
VIDEO_MIME = {
    "video/mp4", "video/webm", "video/quicktime",  # mov
    "video/x-matroska",                            # mkv
    "video/x-msvideo",                             # avi
}
COVER_MIME = {"image/jpeg", "image/png", "image/webp"}


class VideoCommentReq(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)


def _thumb_url(cover_url: str) -> str:
    """从封面 URL 推导缩略图 URL（缩略图文件存在才返回，否则空串供前端回退原图）"""
    if not cover_url or not cover_url.startswith("/uploads/covers/"):
        return ""
    fname = cover_url.rsplit("/", 1)[-1]
    thumb_rel = f"/uploads/covers/thumbs/thumb_{fname}"
    if os.path.exists(os.path.join(STATIC_DIR, thumb_rel.lstrip("/"))):
        return thumb_rel
    return ""


def _probe_duration(path: str) -> int:
    """纯标准库解析 MP4 时长（秒）：遍历顶层 atom 找 moov，在 moov 内找 mvhd。
    返回 0 表示无法解析（非 MP4 容器 / 文件缺失），前端据此隐藏时长角标。"""
    try:
        with open(path, "rb") as f:
            size = os.path.getsize(path)
            # 顶层 atom 扫描
            while f.tell() + 8 <= size:
                head = f.read(8)
                if len(head) < 8:
                    break
                atom_size, atom_type = struct.unpack(">I4s", head)
                if atom_type == b"moov":
                    return _mvhd_duration(f, atom_size - 8 if atom_size > 1 else size - f.tell())
                if atom_size == 1:  # 64 位扩展大小
                    ext = f.read(8)
                    if len(ext) < 8:
                        break
                    atom_size = struct.unpack(">Q", ext)[0]
                if atom_size == 0:
                    atom_size = size - f.tell()
                if atom_size < 8:
                    break
                f.seek(atom_size - 8, 1)
    except Exception:
        return 0
    return 0


def _mvhd_duration(f, moov_body_size: int) -> int:
    """在 moov 内扫描 mvhd，返回时长秒数（0 表示解析失败）"""
    end = f.tell() + moov_body_size
    while f.tell() + 8 <= end:
        head = f.read(8)
        if len(head) < 8:
            break
        atom_size, atom_type = struct.unpack(">I4s", head)
        if atom_type == b"mvhd":
            body = f.read(min(atom_size - 8, 128)) if atom_size > 1 else b""
            if len(body) < 16:
                return 0
            ver = body[0]
            if ver == 1:
                if len(body) < 28:
                    return 0
                timescale = struct.unpack(">I", body[20:24])[0]
                duration = struct.unpack(">Q", body[24:32])[0]
            else:
                if len(body) < 20:
                    return 0
                timescale = struct.unpack(">I", body[12:16])[0]
                duration = struct.unpack(">I", body[16:20])[0]
            if timescale <= 0:
                return 0
            return int(round(duration / timescale))
        if atom_size == 1:
            ext = f.read(8)
            if len(ext) < 8:
                break
            atom_size = struct.unpack(">Q", ext)[0]
        if atom_size < 8:
            break
        f.seek(atom_size - 8, 1)
    return 0


@router.post("/upload")
async def upload(
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    cover: UploadFile = File(None),
    user=Depends(get_current_user),
):
    # 1. 标题 + 描述过审核管线（词典命中即拦）
    audit = audit_text(f"{title} {description}", user["id"], "videos", 0)
    if audit["status"] == "blocked":
        raise HTTPException(status_code=400, detail=f"标题或描述含违规内容，已拦截：{audit['message']}")

    # 2. 校验文件类型与大小，视频保存到 static/videos（可播放 URL /videos/文件名）
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"不支持的视频格式：{ext}，支持 {ALLOWED_EXT}")
    # 批次三：MIME 二次校验，防止伪装扩展名上传非视频文件
    if (file.content_type or "").lower() not in VIDEO_MIME:
        raise HTTPException(status_code=400, detail=f"视频内容类型校验失败：{file.content_type}，仅支持 {sorted(VIDEO_MIME)}")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    fname = f"v_{ts}{ext}"
    fpath = os.path.join(UPLOAD_DIR, fname)
    n = 1
    while os.path.exists(fpath):
        fname = f"v_{ts}_{n}{ext}"
        fpath = os.path.join(UPLOAD_DIR, fname)
        n += 1
    with open(fpath, "wb") as out:
        shutil.copyfileobj(file.file, out, length=1024 * 1024)
    if os.path.getsize(fpath) > MAX_SIZE:
        os.remove(fpath)
        raise HTTPException(status_code=400, detail="文件超过 200MB 上限")
    url = f"/videos/{fname}"

    # 2.5 可选封面保存到 static/uploads/covers（可访问 URL /uploads/covers/封面名）
    #     批次三：封面 MIME + 大小校验，并生成 360px 宽缩略图供列表页加速展示
    cover_url = ""
    thumb_url = ""
    if cover is not None and cover.filename:
        cext = os.path.splitext(cover.filename or "")[1].lower()
        if cext not in ALLOWED_COVER_EXT:
            raise HTTPException(status_code=400, detail=f"不支持的封面格式：{cext}，支持 {ALLOWED_COVER_EXT}")
        if (cover.content_type or "").lower() not in COVER_MIME:
            raise HTTPException(status_code=400, detail=f"封面内容类型校验失败：{cover.content_type}，仅支持 {sorted(COVER_MIME)}")
        os.makedirs(COVER_DIR, exist_ok=True)
        cname = f"cover_{ts}_{uuid.uuid4().hex[:6]}{cext}"
        cpath = os.path.join(COVER_DIR, cname)
        with open(cpath, "wb") as out:
            shutil.copyfileobj(cover.file, out, length=1024 * 1024)
        if os.path.getsize(cpath) > MAX_COVER_SIZE:
            os.remove(cpath)
            raise HTTPException(status_code=400, detail="封面超过 10MB 上限")
        cover_url = f"/uploads/covers/{cname}"
        # 缩略图：等比缩放至 THUMB_WIDTH 宽，存 thumbs 子目录，原图保留
        try:
            from PIL import Image
            os.makedirs(THUMB_DIR, exist_ok=True)
            tname = f"thumb_{cname}"
            tpath = os.path.join(THUMB_DIR, tname)
            with Image.open(cpath) as img:
                img = img.convert("RGB")
                w, h = img.size
                if w > THUMB_WIDTH:
                    img = img.resize((THUMB_WIDTH, max(1, int(h * THUMB_WIDTH / w))), Image.LANCZOS)
                img.save(tpath, "JPEG", quality=82)
            thumb_url = f"/uploads/covers/thumbs/{tname}"
        except Exception:
            # 缩略图失败不阻断上传，仅降级为原图
            thumb_url = ""

    # 3. 入库：落 status=pending，待管理员人工审核（标题/描述仅做拦截判断）；duration 由 MP4 头解析
    duration = _probe_duration(fpath)
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO videos (user_id, title, description, file_path, cover, cover_url, url, status, audit_json, duration) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (user["id"], title, description, fpath, cover_url, cover_url, url,
             STATUS_VIDEO_PENDING, json.dumps(audit, ensure_ascii=False), duration),
        )
        vid = cur.lastrowid
        cur.execute("SELECT * FROM videos WHERE id=?", (vid,))
        row = dict(cur.fetchone())

    row["audit"] = audit
    row["status"] = STATUS_VIDEO_PENDING
    row["thumb_url"] = thumb_url
    return {"video": row, "pending": True}


@router.get("")
def list_videos(category: str = "", page: int = 1, page_size: int = 20):
    """用户端列表：仅展示已审核通过（approved）的视频"""
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    offset = (page - 1) * page_size
    with db_cursor() as cur:
        # 同标题只保留最新一条（历史种子数据存在重复插入，列表/下拉会出现同一视频重复出现）
        total = cur.execute(
            "SELECT COUNT(*) FROM (SELECT MAX(id) AS mid FROM videos WHERE status = ? GROUP BY title)",
            (STATUS_VIDEO_APPROVED,),
        ).fetchone()[0]
        rows = cur.execute(
            """SELECT v.*, u.nickname, u.avatar
               FROM videos v JOIN users u ON v.user_id = u.id
               WHERE v.status = ? AND v.id IN (
                   SELECT MAX(id) FROM videos WHERE status = ? GROUP BY title
               )
               ORDER BY v.created_at DESC LIMIT ? OFFSET ?""",
            (STATUS_VIDEO_APPROVED, STATUS_VIDEO_APPROVED, page_size, offset),
        ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["thumb_url"] = _thumb_url(d.get("cover_url") or "")
        items.append(d)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get("/{video_id}")
def video_detail(video_id: int):
    """用户端详情：仅 approved 视频可访问"""
    with db_cursor() as cur:
        cur.execute(
            """SELECT v.*, u.nickname, u.avatar
               FROM videos v JOIN users u ON v.user_id = u.id
               WHERE v.id=? AND v.status=?""",
            (video_id, STATUS_VIDEO_APPROVED),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="视频不存在或未通过审核")
        cur.execute("UPDATE videos SET view_count = view_count + 1 WHERE id=?", (video_id,))
        v = dict(row)
    v["view_count"] += 1
    v["thumb_url"] = _thumb_url(v.get("cover_url") or "")
    with db_cursor() as cur:
        v["comment_count"] = cur.execute(
            "SELECT COUNT(*) FROM video_comments WHERE video_id=? AND status NOT IN ('blocked','banned')",
            (video_id,),
        ).fetchone()[0]
    return {"video": v}


@router.get("/{video_id}/comments")
def list_video_comments(video_id: int, page: int = 1, page_size: int = 50):
    """视频评论列表：blocked/banned 不返回，join users 返回 nickname/avatar"""
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size
    with db_cursor() as cur:
        cur.execute("SELECT id FROM videos WHERE id=?", (video_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="视频不存在")
        total = cur.execute(
            "SELECT COUNT(*) FROM video_comments WHERE video_id=? AND status NOT IN ('blocked','banned')",
            (video_id,),
        ).fetchone()[0]
        rows = cur.execute(
            """SELECT c.*, u.nickname, u.avatar
               FROM video_comments c JOIN users u ON c.user_id = u.id
               WHERE c.video_id=? AND c.status NOT IN ('blocked','banned')
               ORDER BY c.created_at ASC LIMIT ? OFFSET ?""",
            (video_id, page_size, offset),
        ).fetchall()
    return {"total": total, "page": page, "page_size": page_size, "items": [dict(r) for r in rows]}


@router.post("/{video_id}/comments")
def create_video_comment(video_id: int, req: VideoCommentReq, user=Depends(get_current_user)):
    """发布视频评论：接入审核管线，blocked 拦截；存疑放行展示并上报管理端"""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM videos WHERE id=?", (video_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="视频不存在")

    audit = audit_text(req.content, user["id"], SOURCE_VIDEO_COMMENT, video_id)
    if audit["status"] == "blocked":
        raise HTTPException(status_code=400, detail=f"评论含违规内容，已拦截：{audit['message']}")

    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO video_comments (video_id, user_id, content, status) VALUES (?,?,?,?)",
            (video_id, user["id"], req.content, audit["status"]),
        )
        cid = cur.lastrowid
        cur.execute(
            """SELECT c.*, u.nickname, u.avatar
               FROM video_comments c JOIN users u ON c.user_id = u.id WHERE c.id=?""",
            (cid,),
        )
        comment = dict(cur.fetchone())

    if audit.get("needs_review"):
        enqueue_review(SOURCE_VIDEO_COMMENT, cid, user["id"], req.content,
                       audit.get("review_label", audit.get("label", "")),
                       audit.get("review_risk", "mid"))
        comment["needs_review"] = True
    return {"comment": comment, "audit": audit}


@router.get("/file/{video_id}")
def video_file(video_id: int):
    """流式返回视频文件（播放器用）：仅 approved 可访问"""
    with db_cursor() as cur:
        cur.execute("SELECT file_path FROM videos WHERE id=? AND status=?", (video_id, STATUS_VIDEO_APPROVED))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="视频不存在或未通过审核")
    path = row["file_path"]
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="视频文件缺失")
    return FileResponse(path, media_type="video/mp4")
