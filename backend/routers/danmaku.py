"""弹幕路由：发送（异步审核，先展示后审）/ 拉取（违规弹幕后置处置）"""
import queue
import threading

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db_cursor
from auth import get_current_user
from audit.pipeline import audit_text, audit_batch, enqueue_review
from models import SOURCE_DANMAKU

router = APIRouter(prefix="/api/danmaku", tags=["danmaku"])

# ---- S2 弹幕异步审核：先入库 visible，后台队列审核，违规后置处置 ----
_audit_queue: queue.Queue = queue.Queue()
_audit_thread: threading.Thread | None = None


def _ensure_worker():
    global _audit_thread
    if _audit_thread is None or not _audit_thread.is_alive():
        _audit_thread = threading.Thread(target=_audit_loop, name="danmaku-audit", daemon=True)
        _audit_thread.start()


def _audit_loop():
    """后台审核 worker：FIFO 消费，逐条走完整审核管线，违规后置更新状态。"""
    while True:
        item = _audit_queue.get()
        if item is None:
            break
        danmaku_id, video_id, user_id, content = item
        try:
            audit = audit_text(content, user_id, SOURCE_DANMAKU, video_id)
            # 违规（blocked/folded/warned）：pipeline 已记违规与审计日志，此处同步内容状态
            if audit["status"] != "visible":
                with db_cursor() as cur:
                    cur.execute("UPDATE danmaku SET status=? WHERE id=?",
                                (audit["status"], danmaku_id))
            if audit.get("needs_review"):
                enqueue_review(SOURCE_DANMAKU, danmaku_id, user_id, content,
                               audit.get("review_label", audit.get("label", "")),
                               audit.get("review_risk", "mid"))
        except Exception as exc:
            logger = __import__("logging").getLogger("audit")
            logger.warning("danmaku_async_audit_fail id=%s err=%s", danmaku_id, exc)


class DanmakuReq(BaseModel):
    video_id: int
    content: str = Field(..., min_length=1, max_length=200)


class DanmakuBatchReq(BaseModel):
    video_id: int
    texts: list[str] = Field(..., min_length=1, max_length=50)


@router.post("")
def send_danmaku(req: DanmakuReq, user=Depends(get_current_user)):
    """发送单条弹幕：先入库展示，后台异步审核，违规后置折叠/拦截（S2）"""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM videos WHERE id=?", (req.video_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="视频不存在")
        cur.execute(
            "INSERT INTO danmaku (video_id, user_id, content, status) VALUES (?,?,?,'visible')",
            (req.video_id, user["id"], req.content),
        )
        d = dict(cur.execute(
            "SELECT * FROM danmaku WHERE id=?", (cur.lastrowid,)
        ).fetchone())
    _ensure_worker()
    _audit_queue.put((d["id"], req.video_id, user["id"], req.content))
    return {"danmaku": d, "audit": {"status": "visible", "async_review": True},
            "blocked": False, "message": "已进入异步审核（先展示后审）"}


@router.post("/batch")
def send_danmaku_batch(req: DanmakuBatchReq, user=Depends(get_current_user)):
    """批量发送弹幕：全部先入库展示，逐条异步审核，违规后置处置（S2）"""
    saved = []
    for text in req.texts:
        text = (text or "").strip()
        if not text:
            continue
        with db_cursor() as cur:
            cur.execute(
                "INSERT INTO danmaku (video_id, user_id, content, status) VALUES (?,?,?,'visible')",
                (req.video_id, user["id"], text),
            )
            d = dict(cur.execute(
                "SELECT * FROM danmaku WHERE id=?", (cur.lastrowid,)
            ).fetchone())
        saved.append(d)
        _ensure_worker()
        _audit_queue.put((d["id"], req.video_id, user["id"], text))
    return {"saved": saved, "blocked": [], "message": "已进入异步审核（先展示后审）"}


@router.get("")
def list_danmaku(video_id: int, page: int = 1, page_size: int = 500, limit: int = 0):
    """拉取视频弹幕（分页）；blocked/banned 不返回，folded 返回并带标记（前端折叠演示）"""
    page = max(1, page)
    if limit > 0:
        page_size = min(limit, 2000)
    page_size = min(max(1, page_size), 2000)
    offset = (page - 1) * page_size
    with db_cursor() as cur:
        total = cur.execute(
            """SELECT COUNT(*) FROM danmaku d
               WHERE d.video_id=? AND d.status NOT IN ('blocked','banned')""",
            (video_id,),
        ).fetchone()[0]
        rows = cur.execute(
            """SELECT d.id, d.content, d.status, d.created_at, u.nickname
               FROM danmaku d JOIN users u ON d.user_id = u.id
               WHERE d.video_id=? AND d.status NOT IN ('blocked','banned')
               ORDER BY d.id ASC LIMIT ? OFFSET ?""",
            (video_id, page_size, offset),
        ).fetchall()
    return {"total": total, "page": page, "page_size": page_size, "items": [dict(r) for r in rows]}
