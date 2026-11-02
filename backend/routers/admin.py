"""管理端路由：视频审核 / 存疑队列 / 用户管理 / 违规记录 / 统计"""
import logging
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from db import db_cursor, BASE_DIR
from auth import require_admin
from audit.engine import MODEL_LATENCIES, health as engine_health
from audit.pipeline import _record_violation
from audit import rules
from audit_logs import write_audit_log
from models import (
    STATUS_BANNED,
    STATUS_VIDEO_APPROVED, STATUS_VIDEO_PENDING, STATUS_VIDEO_REJECTED,
    USER_STATUS_ACTIVE, USER_STATUS_BANNED,
    SOURCE_POST, SOURCE_VIDEO,
    SOURCE_DANMAKU, SOURCE_COMMENT, SOURCE_VIDEO_COMMENT, SOURCE_LIVE,
    CREDIT_PENALTY,
    APPEAL_PENDING, APPEAL_APPROVED, APPEAL_REJECTED,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

logger = logging.getLogger("audit")

UPLOAD_DIR = os.path.join(os.path.dirname(BASE_DIR), "uploads")
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")
AUTO_BAN_CREDIT_THRESHOLD = 30  # 信用分低于该值自动封号


def _video_thumb(cover_url: str) -> str:
    """从封面 URL 推导缩略图 URL（文件存在才返回，供管理端列表/预览回退原图）"""
    if not cover_url or not cover_url.startswith("/uploads/covers/"):
        return ""
    fname = cover_url.rsplit("/", 1)[-1]
    thumb_rel = f"/uploads/covers/thumbs/thumb_{fname}"
    if os.path.exists(os.path.join(STATIC_DIR, thumb_rel.lstrip("/"))):
        return thumb_rel
    return ""

_SOURCE_TABLE = {
    SOURCE_POST: "posts",
    SOURCE_VIDEO: "videos",
    SOURCE_DANMAKU: "danmaku",
    SOURCE_COMMENT: "comments",
    SOURCE_VIDEO_COMMENT: "video_comments",
    SOURCE_LIVE: "live_messages",
}


def _today_start() -> str:
    return datetime.now().strftime("%Y-%m-%d 00:00:00")


class VideoReviewReq(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")


class ReviewBanReq(BaseModel):
    pass


class UserBanReq(BaseModel):
    action: str = Field(..., pattern="^(ban|unban)$")
    reason: str = Field("", max_length=200, description="封禁原因")
    duration_hours: int = Field(0, ge=0, le=24 * 365, description="封禁时长（小时），0 表示永久")


class ReviewBatchReq(BaseModel):
    review_ids: list[int] = Field(..., min_length=1, max_length=100)
    action: str = Field(..., pattern="^(ban|clear)$")


class BannedWordReq(BaseModel):
    word: str = Field(..., min_length=1, max_length=50)
    category: str = Field("辱骂暴力", max_length=32)
    risk_level: str = Field("mid", pattern="^(high|mid|low)$")


def _apply_content_ban(cur, source_type: str, source_id: int):
    """将 review_queue 指向的内容标记为 banned（复用外层连接，避免嵌套 db_cursor 死锁）"""
    table = {
        SOURCE_DANMAKU: "danmaku",
        SOURCE_COMMENT: "comments",
        SOURCE_VIDEO_COMMENT: "video_comments",
        SOURCE_LIVE: "live_messages",
    }.get(source_type)
    if table is None:
        return 0
    cur.execute(f"UPDATE {table} SET status=? WHERE id=?", (STATUS_BANNED, source_id))
    return cur.rowcount


def _auto_ban_user(cur, user_id: int):
    """信用分低于阈值自动封禁用户（复用外层连接）。M6：自动封禁写审计日志。"""
    cur.execute("SELECT credit_score FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    if row is not None and row["credit_score"] < AUTO_BAN_CREDIT_THRESHOLD:
        cur.execute("UPDATE users SET status=? WHERE id=?", (USER_STATUS_BANNED, user_id))
        write_audit_log(action="auto_ban", target_type="user", target_id=user_id,
                        detail=f"信用分低于阈值({AUTO_BAN_CREDIT_THRESHOLD})自动封禁", cur=cur)
        logger.info("auto_ban user_id=%s credit=%s", user_id, row["credit_score"])
        return True
    return False


@router.get("/videos/review")
def review_video_list(page: int = 1, page_size: int = 20, user=Depends(require_admin)):
    """待审视频队列（status=pending）"""
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    offset = (page - 1) * page_size
    with db_cursor() as cur:
        # 同标题只保留最新一条待审（历史种子数据存在重复插入，审核队列会出现同一视频重复出现）
        total = cur.execute(
            "SELECT COUNT(*) FROM (SELECT MAX(id) AS mid FROM videos WHERE status=? GROUP BY title)",
            (STATUS_VIDEO_PENDING,),
        ).fetchone()[0]
        rows = cur.execute(
            """SELECT v.*, u.username, u.nickname FROM videos v
               JOIN users u ON v.user_id = u.id
               WHERE v.status=? AND v.id IN (
                   SELECT MAX(id) FROM videos WHERE status=? GROUP BY title
               )
               ORDER BY v.created_at DESC LIMIT ? OFFSET ?""",
            (STATUS_VIDEO_PENDING, STATUS_VIDEO_PENDING, page_size, offset),
        ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["thumb_url"] = _video_thumb(d.get("cover_url") or "")
        items.append(d)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.post("/videos/{video_id}/review")
def review_video(video_id: int, req: VideoReviewReq, user=Depends(require_admin)):
    """视频审核：approve 上架 / reject 驳回"""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM videos WHERE id=?", (video_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="视频不存在")
        new_status = STATUS_VIDEO_APPROVED if req.action == "approve" else STATUS_VIDEO_REJECTED
        cur.execute("UPDATE videos SET status=? WHERE id=?", (new_status, video_id))
        cur.execute(
            """SELECT v.*, u.username, u.nickname FROM videos v
               JOIN users u ON v.user_id = u.id WHERE v.id=?""",
            (video_id,),
        )
        row = dict(cur.fetchone())
        row["thumb_url"] = _video_thumb(row.get("cover_url") or "")
    return {"video": row, "action": req.action}


@router.get("/videos/{video_id}/file")
def review_video_file(video_id: int, user=Depends(require_admin)):
    """管理端流式预览视频文件（待审视频也可播放）"""
    with db_cursor() as cur:
        cur.execute("SELECT file_path FROM videos WHERE id=?", (video_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="视频不存在")
    path = row["file_path"]
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="视频文件缺失")
    return FileResponse(path, media_type="video/mp4")


@router.get("/reviews")
def review_queue_list(page: int = 1, page_size: int = 20, status: str = "pending",
                      risk_level: str = "", source_type: str = "", label: str = "",
                      date_from: str = "", date_to: str = "", sort: str = "created",
                      user=Depends(require_admin)):
    """存疑上报队列：status + risk_level + source_type + 日期筛选；
    排序 sort：created(默认)/risk(高危优先)/reports(举报数优先)（批次二）"""
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    offset = (page - 1) * page_size
    allowed = {"pending", "resolved", "auto_folded"}
    where_parts = []
    params: list = []
    if status == "all":
        pass
    elif status in allowed:
        where_parts.append("r.status=?")
        params.append(status)
    else:
        raise HTTPException(status_code=400, detail="status 仅支持 pending/resolved/auto_folded/all")
    if risk_level:
        if risk_level not in ("high", "mid", "low"):
            raise HTTPException(status_code=400, detail="risk_level 仅支持 high/mid/low")
        where_parts.append("r.risk_level=?")
        params.append(risk_level)
    if source_type:
        where_parts.append("r.source_type=?")
        params.append(source_type)
    if label:
        where_parts.append("r.label=?")
        params.append(label)
    if date_from:
        where_parts.append("r.created_at >= ?")
        params.append(date_from + " 00:00:00")
    if date_to:
        where_parts.append("r.created_at <= ?")
        params.append(date_to + " 23:59:59")
    order_map = {
        "created": "r.created_at DESC, r.id DESC",
        "risk": "CASE r.risk_level WHEN 'high' THEN 0 WHEN 'mid' THEN 1 ELSE 2 END ASC, r.created_at DESC",
        "reports": "report_count DESC, r.created_at DESC",
    }
    order_sql = order_map.get(sort, order_map["created"])
    where_sql = " AND ".join(where_parts) if where_parts else "1=1"
    with db_cursor() as cur:
        total = cur.execute(
            f"SELECT COUNT(*) FROM review_queue r WHERE {where_sql}", params
        ).fetchone()[0]
        rows = cur.execute(
            f"""SELECT r.*, u.username, u.nickname, u.credit_score,
                (SELECT COUNT(*) FROM reports rp
                 WHERE rp.target_type = r.source_type AND rp.target_id = r.source_id
                   AND rp.status = 'pending') AS report_count,
                (SELECT COUNT(*) FROM appeals a WHERE a.source_type = r.source_type AND a.source_id = r.source_id AND a.status = 'pending') AS appeal_count
               FROM review_queue r JOIN users u ON r.user_id = u.id
               WHERE {where_sql}
               ORDER BY {order_sql} LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        ).fetchall()
    return {"total": total, "page": page, "page_size": page_size, "status": status,
            "sort": sort, "items": [dict(r) for r in rows]}


@router.post("/reviews/{review_id}/ban")
def review_ban(review_id: int, user=Depends(require_admin)):
    """确认违规：内容 banned + 记违规 + 扣信用分（低分自动封号）"""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM review_queue WHERE id=?", (review_id,))
        item = cur.fetchone()
        if item is None:
            raise HTTPException(status_code=404, detail="队列条目不存在")
        item = dict(item)
        if item["status"] != "pending":
            raise HTTPException(status_code=400, detail="该条目已处理")

        _apply_content_ban(cur, item["source_type"], item["source_id"])
        _record_violation(
            item["user_id"], item["content"], item["source_type"],
            item["source_id"], item["label"], item["risk_level"], "banned",
            _conn=cur,
        )
        cur.execute(
            "UPDATE review_queue SET status='resolved', action='ban', handled_by=?, handled_at=datetime('now','localtime') WHERE id=?",
            (user["id"], review_id),
        )
        cur.execute(
            "INSERT INTO audit_log (operator_id, action, target_type, target_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "review_ban", item["source_type"], item["source_id"],
             f"确认违规 {item['label']}/{item['risk_level']}"),
        )
        auto_banned = _auto_ban_user(cur, item["user_id"])
        cur.execute("SELECT credit_score, status FROM users WHERE id=?", (item["user_id"],))
        user_state = dict(cur.fetchone())
    logger.info("review_ban review_id=%s user_id=%s source_type=%s source_id=%s label=%s risk=%s auto_banned=%s",
                review_id, item["user_id"], item["source_type"], item["source_id"],
                item["label"], item["risk_level"], auto_banned)
    return {"ok": True, "item": item, "user": user_state, "auto_banned": auto_banned}


@router.post("/reviews/{review_id}/clear")
def review_clear(review_id: int, user=Depends(require_admin)):
    """误判放行：队列 resolved，内容保持 visible；回退已扣信用分（T08）"""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM review_queue WHERE id=?", (review_id,))
        item = cur.fetchone()
        if item is None:
            raise HTTPException(status_code=404, detail="队列条目不存在")
        if item["status"] != "pending":
            raise HTTPException(status_code=400, detail="该条目已处理")

        rollback = _rollback_violation_credit(cur, item["user_id"],
                                              item["source_type"], item["source_id"])
        cur.execute(
            "UPDATE review_queue SET status='resolved', action='clear', handled_by=?, handled_at=datetime('now','localtime') WHERE id=?",
            (user["id"], review_id),
        )
        cur.execute(
            "INSERT INTO audit_log (operator_id, action, target_type, target_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "review_clear", item["source_type"], item["source_id"],
             f"误判放行{rollback}"),
        )
    logger.info("review_clear review_id=%s user_id=%s source_type=%s source_id=%s rollback=%s",
                review_id, item["user_id"], item["source_type"], item["source_id"], rollback)
    return {"ok": True, "action": "clear", "rollback": rollback}


def _rollback_violation_credit(cur, user_id: int, source_type: str, source_id: int) -> dict:
    """误判回退：把该用户同来源内容最近一条未回退违规标记 reverted=1，
    恢复相应信用分并写流水；若用户因此被自动封禁则一并解封。返回回退明细。"""
    result = {"reverted": False, "refunded_credit": 0, "unbanned": False}
    viol = cur.execute(
        """SELECT id, risk_level, label FROM violations
           WHERE user_id=? AND source_type=? AND source_id=? AND reverted=0
           ORDER BY id DESC LIMIT 1""",
        (user_id, source_type, source_id),
    ).fetchone()
    if viol is None:
        return result
    penalty = CREDIT_PENALTY.get(viol["risk_level"], 1)
    cur.execute("UPDATE violations SET reverted=1 WHERE id=?", (viol["id"],))
    cur.execute(
        "UPDATE users SET credit_score = MIN(100, credit_score + ?) WHERE id=?",
        (penalty, user_id),
    )
    cur.execute(
        "INSERT INTO credit_log (user_id, delta, reason, ref_id) VALUES (?,?,?,?)",
        (user_id, penalty, "误判回退", viol["id"]),
    )
    result["reverted"] = True
    result["refunded_credit"] = penalty
    cur.execute("SELECT status FROM users WHERE id=?", (user_id,))
    if cur.fetchone()["status"] == USER_STATUS_BANNED:
        cur.execute(
            "UPDATE users SET status=? WHERE id=?",
            (USER_STATUS_ACTIVE, user_id),
        )
        result["unbanned"] = True
    return result


@router.get("/users")
def list_users(keyword: str = "", phone: str = "", sort: str = "id", page: int = 1,
               page_size: int = 20, user=Depends(require_admin)):
    """用户列表：keyword 模糊搜索（用户名/昵称/手机号）+ phone 精确搜索；排序（id/credit/username/created/status/violations）"""
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    offset = (page - 1) * page_size
    where = ""
    params: list = []
    if keyword:
        kw = f"%{keyword}%"
        where = "WHERE u.username LIKE ? OR u.nickname LIKE ? OR u.phone LIKE ?"
        params = [kw, kw, kw]
    elif phone:
        where = "WHERE u.phone LIKE ?"
        params = [f"%{phone}%"]
    order = {
        "id": "u.id",
        "credit": "u.credit_score DESC, u.id",
        "username": "u.username, u.id",
        "created": "u.created_at DESC, u.id",
        "status": "u.status, u.id",
        "violations": "(SELECT COUNT(*) FROM violations v WHERE v.user_id = u.id) DESC, u.id",
    }.get(sort, "u.id")
    with db_cursor() as cur:
        total = cur.execute(f"SELECT COUNT(*) FROM users u {where}", params).fetchone()[0]
        rows = cur.execute(
            f"""SELECT u.id, u.username, u.nickname, u.phone, u.avatar, u.credit_score,
                       u.role, u.status, u.banned_reason, u.banned_until, u.created_at,
                       (SELECT COUNT(*) FROM violations v WHERE v.user_id = u.id) AS violation_count
                FROM users u {where} ORDER BY {order} LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        ).fetchall()
    return {"total": total, "page": page, "page_size": page_size, "items": [dict(r) for r in rows]}


@router.post("/users/{user_id}/ban")
def ban_user(user_id: int, req: UserBanReq, user=Depends(require_admin)):
    """封禁/解封用户：封禁支持原因与时长（duration_hours>0 时记录到期时间）"""
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="不能操作管理员自己")
    with db_cursor() as cur:
        cur.execute("SELECT id FROM users WHERE id=?", (user_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        if req.action == "ban":
            banned_until = None
            if req.duration_hours > 0:
                banned_until = (datetime.now() + timedelta(hours=req.duration_hours)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            cur.execute(
                "UPDATE users SET status=?, banned_reason=?, banned_until=? WHERE id=?",
                (USER_STATUS_BANNED, req.reason, banned_until, user_id),
            )
            detail = f"原因:{req.reason or '未填写'} 时长:{req.duration_hours}h"
        else:
            cur.execute(
                "UPDATE users SET status=?, banned_reason='', banned_until=NULL WHERE id=?",
                (USER_STATUS_ACTIVE, user_id),
            )
            detail = "解封"
        cur.execute(
            "INSERT INTO audit_log (operator_id, action, target_type, target_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "ban" if req.action == "ban" else "unban", "user", user_id, detail),
        )
        cur.execute(
            """SELECT id, username, nickname, credit_score, role, status,
                      banned_reason, banned_until FROM users WHERE id=?""",
            (user_id,),
        )
        row = dict(cur.fetchone())
    logger.info("user_%s operator=%s target_user=%s detail=%s",
                "ban" if req.action == "ban" else "unban", user["id"], user_id, detail)
    return {"user": row, "action": req.action}


@router.get("/live/rooms")
def admin_live_rooms(user=Depends(require_admin)):
    """管理端直播间列表 + 最近弹幕预览"""
    with db_cursor() as cur:
        rooms = cur.execute(
            """SELECT r.*, u.username, u.nickname FROM live_rooms r
               JOIN users u ON r.user_id = u.id
               ORDER BY r.created_at DESC""",
        ).fetchall()
        items = []
        for r in rooms:
            d = dict(r)
            msgs = cur.execute(
                """SELECT m.id, m.content, m.status, m.created_at, u.nickname
                   FROM live_messages m JOIN users u ON m.user_id = u.id
                   WHERE m.room_id=? ORDER BY m.id DESC LIMIT 20""",
                (d["id"],),
            ).fetchall()
            d["messages"] = [dict(m) for m in msgs]
            items.append(d)
    return {"items": items}


@router.post("/live/rooms/{room_id}/close")
def admin_live_close(room_id: int, user=Depends(require_admin)):
    """管理端强制下播"""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM live_rooms WHERE id=?", (room_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="直播间不存在")
        cur.execute("UPDATE live_rooms SET status='off' WHERE id=?", (room_id,))
        cur.execute("SELECT * FROM live_rooms WHERE id=?", (room_id,))
        row = dict(cur.fetchone())
    try:
        from routers.live import _room_connections
        _room_connections.pop(room_id, None)
    except Exception:
        pass
    return {"room": row, "action": "close"}


@router.get("/violations")
def list_violations(page: int = 1, page_size: int = 30, user=Depends(require_admin)):
    """待复核队列：最近违规记录"""
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size
    with db_cursor() as cur:
        total = cur.execute("SELECT COUNT(*) FROM violations").fetchone()[0]
        rows = cur.execute(
            """SELECT v.*, u.username, u.nickname, u.credit_score
               FROM violations v JOIN users u ON v.user_id = u.id
               ORDER BY v.created_at DESC LIMIT ? OFFSET ?""",
            (page_size, offset),
        ).fetchall()
    return {"total": total, "page": page, "page_size": page_size, "items": [dict(r) for r in rows]}


@router.get("/stats")
def stats(user=Depends(require_admin)):
    """平台健康度 + 六类分布 + 拦截趋势"""
    today = _today_start()
    with db_cursor() as cur:
        # 六类分布
        labels = cur.execute(
            "SELECT label, COUNT(*) AS cnt FROM violations GROUP BY label ORDER BY cnt DESC"
        ).fetchall()
        # 近 7 天拦截趋势
        rows7 = cur.execute(
            """SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS cnt
               FROM violations WHERE created_at >= datetime('now', 'localtime', '-6 days')
               GROUP BY day ORDER BY day""",
        ).fetchall()
        trend = [dict(r) for r in rows7]
        # 今日拦截量 & 内容总量（拦截率口径）
        today_violations = cur.execute(
            "SELECT COUNT(*) FROM violations WHERE created_at >= ?", (today,)
        ).fetchone()[0]
        today_posts = cur.execute(
            "SELECT COUNT(*) FROM posts WHERE created_at >= ?", (today,)
        ).fetchone()[0]
        today_comments = cur.execute(
            "SELECT COUNT(*) FROM comments WHERE created_at >= ?", (today,)
        ).fetchone()[0]
        today_danmaku = cur.execute(
            "SELECT COUNT(*) FROM danmaku WHERE created_at >= ?", (today,)
        ).fetchone()[0]
        today_videos = cur.execute(
            "SELECT COUNT(*) FROM videos WHERE created_at >= ?", (today,)
        ).fetchone()[0]
        # 总违规量 & 高危占比
        total_violations = cur.execute("SELECT COUNT(*) FROM violations").fetchone()[0]
        high_risk = cur.execute(
            "SELECT COUNT(*) FROM violations WHERE risk_level = 'high'"
        ).fetchone()[0]

    total_content = today_posts + today_comments + today_danmaku + today_videos
    block_rate = round(today_violations / total_content * 100, 2) if total_content else 0.0
    avg_latency = round(sum(MODEL_LATENCIES) / len(MODEL_LATENCIES), 2) if MODEL_LATENCIES else None

    return {
        "today_violations": today_violations,
        "total_violations": total_violations,
        "high_risk_count": high_risk,
        "block_rate": block_rate,
        "avg_latency_ms": avg_latency,
        "today_content_total": total_content,
        "label_distribution": [dict(r) for r in labels],
        "trend": trend,
    }


@router.get("/engine/health")
def admin_engine_health(user=Depends(require_admin)):
    """识别服务健康状态：在线/离线 + 最近采样延迟（批次一新增）"""
    ok = engine_health()
    avg = round(sum(MODEL_LATENCIES) / len(MODEL_LATENCIES), 2) if MODEL_LATENCIES else None
    today = _today_start()
    with db_cursor() as cur:
        today_blocked = cur.execute(
            "SELECT COUNT(*) FROM violations WHERE created_at >= ?", (today,)
        ).fetchone()[0]
        today_folded = cur.execute(
            "SELECT COUNT(*) FROM review_queue WHERE status='auto_folded' AND created_at >= ?", (today,)
        ).fetchone()[0]
        today_pending = cur.execute(
            "SELECT COUNT(*) FROM review_queue WHERE status='pending' AND created_at >= ?", (today,)
        ).fetchone()[0]
        handled_today = cur.execute(
            "SELECT COUNT(*) FROM review_queue WHERE handled_at IS NOT NULL AND handled_at >= ?", (today,)
        ).fetchone()[0]
        resolved_today = cur.execute(
            "SELECT COUNT(*) FROM review_queue WHERE handled_at IS NOT NULL AND handled_at >= ? AND action IN ('ban','clear')", (today,)
        ).fetchone()[0]
        try:
            word_count = cur.execute(
                "SELECT COUNT(*) FROM banned_words WHERE enabled=1"
            ).fetchone()[0]
        except Exception:
            word_count = 0
    batch_success_rate = round(resolved_today * 100 / handled_today, 1) if handled_today else None
    dict_online = bool(rules._loaded and rules._index) or word_count > 0
    return {
        "online": ok,
        "model_online": ok,
        "dictionary_online": dict_online,
        "dictionary_count": max(len(rules._index) if rules._loaded else 0, word_count),
        "database_online": True,
        "avg_latency_ms": avg,
        "model_latencies_sampled": len(MODEL_LATENCIES),
        "today_blocked": today_blocked,
        "today_folded": today_folded,
        "today_pending": today_pending,
        "batch_success_rate": batch_success_rate,
        "message": "识别服务在线" if ok else "识别服务离线，仅词典可用",
    }


@router.get("/reviews/{review_id}/context")
def review_context(review_id: int, user=Depends(require_admin)):
    """存疑条目上下文：队列详情 + 源内容全文 + 用户最近内容 + 最近违规（批次一新增）"""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM review_queue WHERE id=?", (review_id,))
        item = cur.fetchone()
        if item is None:
            raise HTTPException(status_code=404, detail="队列条目不存在")
        item = dict(item)

        ctx = {"source": None}
        table = _SOURCE_TABLE.get(item["source_type"])
        if table:
            cur.execute(f"SELECT * FROM {table} WHERE id=?", (item["source_id"],))
            row = cur.fetchone()
            ctx["source"] = dict(row) if row else None

        recent = []
        for t in ("posts", "comments", "danmaku", "video_comments", "live_messages"):
            try:
                cur.execute(
                    f"""SELECT ? AS src, id, content, status, created_at
                        FROM {t} WHERE user_id=? ORDER BY id DESC LIMIT 5""",
                    (t, item["user_id"]),
                )
                recent.extend(dict(r) for r in cur.fetchall())
            except Exception:
                continue
        recent.sort(key=lambda x: x["created_at"] or "", reverse=True)

        violations = cur.execute(
            """SELECT id, content, label, risk_level, action, reverted, created_at
               FROM violations WHERE user_id=? ORDER BY id DESC LIMIT 10""",
            (item["user_id"],),
        ).fetchall()
        cur.execute(
            "SELECT credit_score, status, banned_reason, banned_until FROM users WHERE id=?",
            (item["user_id"],),
        )
        user_state = dict(cur.fetchone())
    matched = rules.quick_check(item.get("content") or "")
    return {
        "review": item,
        "context": ctx,
        "recent_content": recent[:10],
        "violations": [dict(v) for v in violations],
        "matched_words": (matched[2] if matched else []),
        "matched_label": (matched[0] if matched else ""),
        "user": user_state,
    }


@router.post("/reviews/batch")
def review_batch(req: ReviewBatchReq, user=Depends(require_admin)):
    """批量处置存疑队列：ban 确认违规 / clear 误判放行（批次一新增）"""
    results = []
    with db_cursor() as cur:
        for rid in req.review_ids:
            cur.execute("SELECT * FROM review_queue WHERE id=?", (rid,))
            item = cur.fetchone()
            if item is None:
                results.append({"review_id": rid, "ok": False, "detail": "不存在"})
                continue
            if item["status"] != "pending":
                results.append({"review_id": rid, "ok": False, "detail": "已处理"})
                continue
            if req.action == "ban":
                _apply_content_ban(cur, item["source_type"], item["source_id"])
                _record_violation(
                    item["user_id"], item["content"], item["source_type"],
                    item["source_id"], item["label"], item["risk_level"], "banned",
                    _conn=cur,
                )
                cur.execute(
                    "UPDATE review_queue SET status='resolved', action='ban', handled_by=?, handled_at=datetime('now','localtime') WHERE id=?",
                    (user["id"], rid),
                )
                auto_banned = _auto_ban_user(cur, item["user_id"])
                results.append({"review_id": rid, "ok": True, "detail": "ban",
                                "auto_banned": auto_banned})
            else:
                rollback = _rollback_violation_credit(cur, item["user_id"],
                                                      item["source_type"], item["source_id"])
                cur.execute(
                    "UPDATE review_queue SET status='resolved', action='clear', handled_by=?, handled_at=datetime('now','localtime') WHERE id=?",
                    (user["id"], rid),
                )
                results.append({"review_id": rid, "ok": True, "detail": "clear",
                                "rollback": rollback})
            cur.execute(
                "INSERT INTO audit_log (operator_id, action, target_type, target_id, detail) VALUES (?,?,?,?,?)",
                (user["id"], f"batch_{req.action}", "review", rid, ""),
            )
    logger.info("review_batch operator=%s action=%s ids=%s ok=%s",
                user["id"], req.action, req.review_ids,
                [r["ok"] for r in results])
    return {"ok": True, "action": req.action, "results": results}


@router.get("/banned_words")
def admin_banned_words(page: int = 1, page_size: int = 50, user=Depends(require_admin)):
    """管理端维护的违规词列表（banned_words 表，分页）"""
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size
    with db_cursor() as cur:
        total = cur.execute("SELECT COUNT(*) FROM banned_words").fetchone()[0]
        rows = cur.execute(
            """SELECT id, word, category, risk_level, enabled, created_at
               FROM banned_words ORDER BY id DESC LIMIT ? OFFSET ?""",
            (page_size, offset),
        ).fetchall()
    return {"total": total, "page": page, "page_size": page_size, "items": [dict(r) for r in rows]}


@router.post("/banned_words")
def admin_banned_word_add(req: BannedWordReq, user=Depends(require_admin)):
    """新增违规词（同名词存在时直接重新启用并更新属性），写入后重载词典立即生效"""
    word = req.word.strip().lower()
    if not word:
        raise HTTPException(status_code=400, detail="违规词不能为空")
    with db_cursor() as cur:
        cur.execute("SELECT id FROM banned_words WHERE word=?", (word,))
        exist = cur.fetchone()
        if exist:
            cur.execute(
                "UPDATE banned_words SET category=?, risk_level=?, enabled=1 WHERE id=?",
                (req.category, req.risk_level, exist["id"]),
            )
            wid = exist["id"]
            created = False
        else:
            cur.execute(
                "INSERT INTO banned_words (word, category, risk_level) VALUES (?,?,?)",
                (word, req.category, req.risk_level),
            )
            wid = cur.lastrowid
            created = True
        cur.execute("SELECT * FROM banned_words WHERE id=?", (wid,))
        row = dict(cur.fetchone())
    rules.reload_dictionary()
    return {"created": created, "word": row}


@router.delete("/banned_words/{word_id}")
def admin_banned_word_delete(word_id: int, user=Depends(require_admin)):
    """删除违规词（从维护表移除），重载词典立即生效"""
    with db_cursor() as cur:
        cur.execute("SELECT id, word FROM banned_words WHERE id=?", (word_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="违规词不存在")
        cur.execute("DELETE FROM banned_words WHERE id=?", (word_id,))
    rules.reload_dictionary()
    return {"ok": True, "deleted": {"id": row["id"], "word": row["word"]}}


@router.get("/audit-logs")
def admin_audit_logs(page: int = 1, page_size: int = 20, operator_id: int = 0,
                     action: str = "", user=Depends(require_admin)):
    """审计日志列表（M6）：分页 + 操作者 + 动作类型筛选

    action 示例：dict_block / dict_fold / dict_warn / model_block / review_enqueue /
    review_ban / review_clear / batch_ban / batch_clear / review_auto_fold /
    auto_ban / ban / unban / appeal_submit / appeal_review / live_mute / live_unmute / live_kick
    """
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size
    where_parts = []
    params: list = []
    if operator_id:
        where_parts.append("a.operator_id=?")
        params.append(operator_id)
    if action:
        where_parts.append("a.action=?")
        params.append(action)
    where_sql = " AND ".join(where_parts) if where_parts else "1=1"
    with db_cursor() as cur:
        total = cur.execute(
            f"SELECT COUNT(*) FROM audit_log a WHERE {where_sql}", params
        ).fetchone()[0]
        rows = cur.execute(
            f"""SELECT a.id, a.operator_id, a.action, a.target_type, a.target_id,
                       a.detail, a.created_at, u.username AS operator_name
               FROM audit_log a LEFT JOIN users u ON a.operator_id = u.id
               WHERE {where_sql}
               ORDER BY a.id DESC LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        ).fetchall()
    return {
        "total": total, "page": page, "page_size": page_size,
        "operator_id": operator_id or None, "action": action or None,
        "items": [dict(r) for r in rows],
    }


class AppealReviewReq(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    reply: str = Field("", max_length=500, description="处置回复（可选）")


@router.post("/appeals/{appeal_id}/review")
def admin_appeal_review(appeal_id: int, req: AppealReviewReq, user=Depends(require_admin)):
    """申诉处置（M6 补审计闭环）：approve 通过（回退扣分/解封） / reject 驳回"""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM appeals WHERE id=?", (appeal_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="申诉不存在")
        if row["status"] != APPEAL_PENDING:
            raise HTTPException(status_code=400, detail="该申诉已处理")
        new_status = APPEAL_APPROVED if req.action == "approve" else APPEAL_REJECTED
        cur.execute(
            "UPDATE appeals SET status=?, reply=?, handled_by=?, handled_at=datetime('now','localtime') WHERE id=?",
            (new_status, req.reply, user["id"], appeal_id),
        )
        detail = f"申诉{'通过' if req.action == 'approve' else '驳回'}"
        if req.action == "approve":
            rollback = _rollback_violation_credit(
                cur, row["user_id"], row["source_type"], row["source_id"]
            )
            detail += f"，回退违规与信用分 {rollback}"
        write_audit_log(operator_id=user["id"], action="appeal_review",
                        target_type="appeal", target_id=appeal_id, detail=detail, cur=cur)
        cur.execute(
            """SELECT a.*, u.username, u.nickname FROM appeals a
               JOIN users u ON a.user_id = u.id WHERE a.id=?""",
            (appeal_id,),
        )
        item = dict(cur.fetchone())
    logger.info("appeal_review operator=%s appeal_id=%s action=%s reply=%s",
                user["id"], appeal_id, req.action, req.reply or "")
    return {"ok": True, "action": req.action, "appeal": item}
