"""举报路由：用户一键举报（弹幕/评论/视频/帖子/直播弹幕）+ 管理端待处理举报列表与处置

批次二新增：举报作为人工审核的辅助信号，review_queue 与违规处置会引用举报次数加权。
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db_cursor
from auth import get_current_user, require_admin
from models import (
    SOURCE_POST, SOURCE_VIDEO, SOURCE_DANMAKU, SOURCE_COMMENT,
    SOURCE_VIDEO_COMMENT, SOURCE_LIVE,
)

router = APIRouter(tags=["reports"])
logger = logging.getLogger("audit")

VALID_TARGETS = {
    SOURCE_POST: "posts",
    SOURCE_VIDEO: "videos",
    SOURCE_DANMAKU: "danmaku",
    SOURCE_COMMENT: "comments",
    SOURCE_VIDEO_COMMENT: "video_comments",
    SOURCE_LIVE: "live_messages",
}


class ReportReq(BaseModel):
    target_type: str = Field(..., pattern="^(posts|videos|danmaku|comments|video_comments|live_messages)$")
    target_id: int = Field(..., gt=0)
    reason: str = Field("", max_length=200, description="举报理由，可选")


@router.post("/api/reports")
def create_report(req: ReportReq, user=Depends(get_current_user)):
    """一键举报：校验目标存在；同一举报人对同一目标存在 pending 举报时不重复创建"""
    table = VALID_TARGETS.get(req.target_type)
    if table is None:
        raise HTTPException(status_code=400, detail="不支持的举报对象类型")
    with db_cursor() as cur:
        try:
            row = cur.execute(f"SELECT id FROM {table} WHERE id=?", (req.target_id,)).fetchone()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"目标表不存在: {exc}") from exc
        if row is None:
            raise HTTPException(status_code=404, detail="举报目标不存在")
        dup = cur.execute(
            """SELECT id FROM reports
               WHERE user_id=? AND target_type=? AND target_id=? AND status='pending'""",
            (user["id"], req.target_type, req.target_id),
        ).fetchone()
        if dup is not None:
            return {"ok": True, "duplicated": True, "report_id": dup["id"],
                    "message": "你已举报过该内容，等待管理员处理"}
        cur.execute(
            "INSERT INTO reports (user_id, target_type, target_id, reason) VALUES (?,?,?,?)",
            (user["id"], req.target_type, req.target_id, req.reason.strip()),
        )
        rid = cur.lastrowid
    logger.info("report_created user_id=%s target_type=%s target_id=%s reason=%s",
                user["id"], req.target_type, req.target_id, req.reason[:30])
    return {"ok": True, "report_id": rid, "message": "举报已提交，感谢反馈"}


@router.get("/api/admin/reports")
def admin_reports(status: str = "pending", page: int = 1, page_size: int = 20,
                  user=Depends(require_admin)):
    """管理端举报列表：默认 pending，可按 status(resolved/all) 筛选"""
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    offset = (page - 1) * page_size
    where = "r.status=?" if status != "all" else "1=1"
    params: list = [status] if status != "all" else []
    with db_cursor() as cur:
        total = cur.execute(f"SELECT COUNT(*) FROM reports r WHERE {where}", params).fetchone()[0]
        rows = cur.execute(
            f"""SELECT r.*, u.username AS reporter_name, u.nickname AS reporter_nick
               FROM reports r
               JOIN users u ON r.user_id = u.id
               WHERE {where}
               ORDER BY r.id DESC LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        ).fetchall()
        items = []
        for r in rows:
            d = dict(r)
            # 补被举报内容摘要与所有者（供审核辅助参考）
            table = VALID_TARGETS.get(d["target_type"])
            if table:
                # videos 表无 content 列，用 title 作摘要
                src_col = "title AS content" if table == "videos" else "content"
                src = cur.execute(f"SELECT id, {src_col}, user_id FROM {table} WHERE id=?",
                                  (d["target_id"],)).fetchone()
                if src:
                    d["target_content"] = src["content"]
                    owner = cur.execute(
                        "SELECT username, nickname FROM users WHERE id=?", (src["user_id"],)
                    ).fetchone()
                    d["target_owner"] = dict(owner) if owner else None
            items.append(d)
    return {"total": total, "page": page, "page_size": page_size,
            "status": status, "items": items}


@router.post("/api/admin/reports/{report_id}/resolve")
def admin_report_resolve(report_id: int, user=Depends(require_admin)):
    """举报处置完成（标记 resolved），不影响被举报内容状态（供人工审核辅助参考）"""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM reports WHERE id=?", (report_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="举报不存在")
        cur.execute(
            "UPDATE reports SET status='resolved', handled_by=?, handled_at=datetime('now','localtime') WHERE id=?",
            (user["id"], report_id),
        )
    logger.info("report_resolved operator=%s report_id=%s", user["id"], report_id)
    return {"ok": True, "report_id": report_id}
