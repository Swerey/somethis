"""帖子路由：发帖/列表/详情/评论/点赞/关注/实时预检"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db_cursor
from auth import get_current_user
from audit.pipeline import audit_post, audit_text, enqueue_review
from audit import rules, engine
from models import SOURCE_COMMENT, SOURCE_POST

router = APIRouter(prefix="/api/posts", tags=["posts"])


class PostReq(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=5000)
    category: str = Field("闲聊", max_length=20)
    summary: str = Field("", max_length=200, description="帖子简介，可选；不传则自动从正文截取")


class CommentReq(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)


class PrecheckReq(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


def _post_dict(row, cur):
    p = dict(row)
    # 列表接口已通过聚合子查询带回 comment_count，避免 N+1 逐行 COUNT
    if "comment_count" not in p:
        cur.execute("SELECT COUNT(*) FROM comments WHERE post_id=?", (p["id"],))
        p["comment_count"] = cur.fetchone()[0]
    return p


@router.post("/precheck")
def precheck(req: PrecheckReq):
    """编辑时实时预检：返回违规提示，不落库不扣分"""
    hit = rules.quick_check(req.text)
    if hit is not None:
        label, risk, words = hit
        return {"safe": False, "label": label, "risk": risk, "words": words,
                "message": f"命中违规词：{'、'.join(words)}（{label}）"}
    resp = engine.predict([req.text])
    if resp is None:
        return {"safe": True, "message": "识别服务暂不可用，预检跳过", "words": []}
    item = resp["results"][0]
    if item.get("label", "正常") == "正常":
        return {"safe": True, "message": "内容正常", "words": []}
    return {"safe": False, "label": item.get("label"), "risk": "mid", "words": [],
            "message": f"模型判定疑似{item.get('label')}"}


@router.post("")
def create_post(req: PostReq, user=Depends(get_current_user)):
    audit = audit_post(req.title, req.content, user["id"], 0)
    if audit["status"] == "blocked":
        raise HTTPException(status_code=400, detail=f"帖子含违规内容，已拦截：{audit['message']}")
    summary = (req.summary or "").strip()
    if not summary:
        summary = " ".join(req.content.split())[:80]
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO posts (user_id, title, content, category, status, summary) VALUES (?,?,?,?,?,?)",
            (user["id"], req.title, req.content, req.category, audit["status"], summary),
        )
        pid = cur.lastrowid
        cur.execute(
            """SELECT p.*, u.nickname, u.avatar
               FROM posts p JOIN users u ON p.user_id = u.id WHERE p.id=?""",
            (pid,),
        )
        post = _post_dict(cur.fetchone(), cur)
    if audit.get("needs_review"):
        enqueue_review(SOURCE_POST, pid, user["id"], req.content,
                       audit.get("review_label", audit.get("label", "")),
                       audit.get("review_risk", "mid"))
        post["needs_review"] = True
    return {"post": post, "audit": audit}


@router.get("")
def list_posts(category: str = "", tab: str = "latest", page: int = 1, page_size: int = 20):
    """tab: latest 最新 / hot 精华(热榜，按点赞数)"""
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    offset = (page - 1) * page_size
    where = "WHERE p.status != 'blocked'"
    params = []
    if category and category != "推荐":
        where += " AND p.category = ?"
        params.append(category)
    order = "p.created_at DESC" if tab == "latest" else "p.like_count DESC, p.created_at DESC"
    with db_cursor() as cur:
        total = cur.execute(f"SELECT COUNT(*) FROM posts p {where}", params).fetchone()[0]
        rows = cur.execute(
            f"""SELECT p.*, u.nickname, u.avatar,
                       (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count
                FROM posts p
                JOIN users u ON p.user_id = u.id {where}
                ORDER BY {order} LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        ).fetchall()
        items = [_post_dict(r, cur) for r in rows]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/{post_id}")
def post_detail(post_id: int, page: int = 1, page_size: int = 100):
    page = max(1, page)
    page_size = min(max(1, page_size), 500)
    offset = (page - 1) * page_size
    with db_cursor() as cur:
        cur.execute(
            """SELECT p.*, u.nickname, u.avatar
               FROM posts p JOIN users u ON p.user_id = u.id WHERE p.id=?""",
            (post_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="帖子不存在")
        post = _post_dict(row, cur)
        total = cur.execute(
            "SELECT COUNT(*) FROM comments WHERE post_id=? AND status NOT IN ('blocked','banned')",
            (post_id,),
        ).fetchone()[0]
        cur.execute(
            """SELECT c.*, u.nickname, u.avatar FROM comments c
               JOIN users u ON c.user_id = u.id
               WHERE c.post_id=? AND c.status NOT IN ('blocked','banned')
               ORDER BY c.created_at ASC LIMIT ? OFFSET ?""",
            (post_id, page_size, offset),
        )
        comments = [dict(r) for r in cur.fetchall()]
    return {"post": post, "comments": comments, "total": total,
            "page": page, "page_size": page_size}


@router.post("/{post_id}/comments")
def create_comment(post_id: int, req: CommentReq, user=Depends(get_current_user)):
    audit = audit_text(req.content, user["id"], SOURCE_COMMENT, post_id)
    if audit["status"] == "blocked":
        raise HTTPException(status_code=400, detail=f"评论含违规内容，已拦截：{audit['message']}")
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO comments (post_id, user_id, content, status) VALUES (?,?,?,?)",
            (post_id, user["id"], req.content, audit["status"]),
        )
        cur.execute("UPDATE posts SET comment_count = comment_count + 1 WHERE id=?", (post_id,))
        cid = cur.lastrowid
        cur.execute(
            """SELECT c.*, u.nickname, u.avatar FROM comments c
               JOIN users u ON c.user_id = u.id WHERE c.id=?""",
            (cid,),
        )
        comment = dict(cur.fetchone())
    if audit.get("needs_review"):
        enqueue_review(SOURCE_COMMENT, cid, user["id"], req.content,
                       audit.get("review_label", audit.get("label", "")),
                       audit.get("review_risk", "mid"))
        comment["needs_review"] = True
    return {"comment": comment, "audit": audit}


@router.post("/{post_id}/like")
def like_post(post_id: int, user=Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute("SELECT id FROM posts WHERE id=?", (post_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="帖子不存在")
        cur.execute("SELECT id FROM post_likes WHERE post_id=? AND user_id=?", (post_id, user["id"]))
        liked = cur.fetchone()
        if liked:
            cur.execute("DELETE FROM post_likes WHERE id=?", (liked["id"],))
            cur.execute("UPDATE posts SET like_count = MAX(0, like_count - 1) WHERE id=?", (post_id,))
            liked_flag = False
        else:
            cur.execute("INSERT INTO post_likes (post_id, user_id) VALUES (?,?)", (post_id, user["id"]))
            cur.execute("UPDATE posts SET like_count = like_count + 1 WHERE id=?", (post_id,))
            liked_flag = True
        cur.execute("SELECT like_count FROM posts WHERE id=?", (post_id,))
        like_count = cur.fetchone()["like_count"]
    return {"liked": liked_flag, "like_count": like_count}


@router.post("/user/{target_id}/follow")
def follow_user(target_id: int, user=Depends(get_current_user)):
    if target_id == user["id"]:
        raise HTTPException(status_code=400, detail="不能关注自己")
    with db_cursor() as cur:
        cur.execute("SELECT id FROM users WHERE id=?", (target_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        cur.execute("SELECT id FROM follows WHERE user_id=? AND follow_user_id=?", (user["id"], target_id))
        existed = cur.fetchone()
        if existed:
            cur.execute("DELETE FROM follows WHERE id=?", (existed["id"],))
            following = False
        else:
            cur.execute("INSERT INTO follows (user_id, follow_user_id) VALUES (?,?)", (user["id"], target_id))
            following = True
    return {"following": following}


@router.get("/users/active")
def active_users(limit: int = 10):
    """活跃用户榜：按 帖子+评论+弹幕 内容量统计"""
    with db_cursor() as cur:
        # 一次 LEFT JOIN 聚合替代三组相关子查询（每用户 3 次扫描 -> 1 次分组聚合）
        rows = cur.execute(
            """SELECT u.id, u.username, u.nickname, u.avatar, u.credit_score,
                      COUNT(DISTINCT p.id) AS pc,
                      COUNT(DISTINCT c.id) AS cc,
                      COUNT(DISTINCT d.id) AS dc
               FROM users u
               LEFT JOIN posts p ON p.user_id = u.id
               LEFT JOIN comments c ON c.user_id = u.id
               LEFT JOIN danmaku d ON d.user_id = u.id
               GROUP BY u.id
               ORDER BY (pc + cc + dc) DESC, u.id ASC
               LIMIT ?""",
            (min(max(1, limit), 50),),
        ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["activity"] = d["pc"] + d["cc"] + d["dc"]
        items.append(d)
    return {"items": items}
