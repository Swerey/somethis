"""用户公开资料路由：他人主页资料 / 帖子列表 / 视频列表（仅公开字段，不含隐私）"""
from fastapi import APIRouter, HTTPException

from db import db_cursor
from models import STATUS_VIDEO_APPROVED

router = APIRouter(prefix="/api/users", tags=["users"])


def _get_user_or_404(cur, user_id: int) -> dict:
    """取用户行，不存在抛 404"""
    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return dict(row)


def _post_dict(row, cur):
    p = dict(row)
    cur.execute("SELECT COUNT(*) FROM comments WHERE post_id=?", (p["id"],))
    p["comment_count"] = cur.fetchone()[0]
    return p


@router.get("/{user_id}")
def user_profile(user_id: int):
    """公开资料：id/username/nickname/avatar/信用分/违规次数/注册时间/状态与内容统计（不含 phone 等隐私）"""
    with db_cursor() as cur:
        u = _get_user_or_404(cur, user_id)
        violation_count = cur.execute(
            "SELECT COUNT(*) FROM violations WHERE user_id=? AND reverted=0", (user_id,)
        ).fetchone()[0]
        post_count = cur.execute(
            "SELECT COUNT(*) FROM posts WHERE user_id=? AND status != 'blocked'", (user_id,)
        ).fetchone()[0]
        video_count = cur.execute(
            "SELECT COUNT(*) FROM videos WHERE user_id=? AND status=?", (user_id, STATUS_VIDEO_APPROVED)
        ).fetchone()[0]
        following_count = cur.execute(
            "SELECT COUNT(*) FROM follows WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        follower_count = cur.execute(
            "SELECT COUNT(*) FROM follows WHERE follow_user_id=?", (user_id,)
        ).fetchone()[0]
    return {
        "id": u["id"],
        "username": u["username"],
        "nickname": u["nickname"],
        "avatar": u["avatar"],
        "credit_score": u["credit_score"],
        "status": u["status"],
        "created_at": u["created_at"],
        "violation_count": violation_count,
        "post_count": post_count,
        "video_count": video_count,
        "following_count": following_count,
        "follower_count": follower_count,
    }


@router.get("/{user_id}/posts")
def user_posts(user_id: int, page: int = 1, page_size: int = 20):
    """该用户帖子列表：仅公开（非 blocked），含简介 summary 字段"""
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    offset = (page - 1) * page_size
    where = "WHERE p.user_id=? AND p.status != 'blocked'"
    params = [user_id]
    with db_cursor() as cur:
        _get_user_or_404(cur, user_id)
        total = cur.execute(f"SELECT COUNT(*) FROM posts p {where}", params).fetchone()[0]
        rows = cur.execute(
            f"""SELECT p.*, u.nickname, u.avatar FROM posts p
                JOIN users u ON p.user_id = u.id {where}
                ORDER BY p.created_at DESC LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        ).fetchall()
        items = [_post_dict(r, cur) for r in rows]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/{user_id}/videos")
def user_videos(user_id: int, page: int = 1, page_size: int = 20):
    """该用户视频列表：仅展示已审核通过（approved）的视频"""
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    offset = (page - 1) * page_size
    with db_cursor() as cur:
        _get_user_or_404(cur, user_id)
        total = cur.execute(
            "SELECT COUNT(*) FROM videos WHERE user_id=? AND status=?",
            (user_id, STATUS_VIDEO_APPROVED),
        ).fetchone()[0]
        rows = cur.execute(
            """SELECT v.*, u.nickname, u.avatar
               FROM videos v JOIN users u ON v.user_id = u.id
               WHERE v.user_id=? AND v.status=?
               ORDER BY v.created_at DESC LIMIT ? OFFSET ?""",
            (user_id, STATUS_VIDEO_APPROVED, page_size, offset),
        ).fetchall()
    return {"total": total, "page": page, "page_size": page_size, "items": [dict(r) for r in rows]}
