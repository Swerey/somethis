"""主页推荐轮播：公开聚合接口 + 管理端置顶管理接口

- GET /api/carousel        ：置顶优先 + 热度/最新交替聚合，上限 8
- POST /api/admin/carousel ：新增/更新置顶项（幂等，同类型+目标重复则更新）
- DELETE /api/admin/carousel/{id} ：取消置顶
- PUT  /api/admin/carousel/{id}   ：更新置顶项（排序/生效时间）

置顶项仅存 carousel_items 表，聚合项每次动态计算，目标被删除/封禁时自动跳过。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db_cursor
from auth import require_admin

router = APIRouter(prefix="/api", tags=["carousel"])

MAX_ITEMS = 8
HOT_TAKE = 6
LATEST_TAKE = 2
INSERT_POSITIONS = {2, 5}  # 最新帖穿插位置（热度为主、穿插 1-2 个最新）


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _item_url(kind: str, tid: int) -> str:
    return f"post.html?id={tid}" if kind == "post" else f"video.html?id={tid}"


def _fetch_target(cur, kind: str, tid: int):
    """拉取目标详情；帖子需 visible、视频需 approved，否则视为不可用返回 None。"""
    if kind == "post":
        row = cur.execute(
            "SELECT id, title, summary, category, like_count, comment_count, status "
            "FROM posts WHERE id=?",
            (tid,),
        ).fetchone()
        if not row or row["status"] != "visible":
            return None
        return dict(row)
    row = cur.execute(
        "SELECT id, title, description, cover_url, view_count, status FROM videos WHERE id=?",
        (tid,),
    ).fetchone()
    if not row or row["status"] != "approved":
        return None
    return dict(row)


def _build(kind: str, tid: int, t: dict, pinned: bool = False, pinned_id: int = 0) -> dict:
    cover = t.get("cover_url") or None if kind == "video" else None
    return {
        "id": pinned_id,
        "kind": kind,
        "target_id": tid,
        "title": t["title"],
        "summary": t.get("summary") or t.get("description") or "",
        "cover_url": cover,
        "url": _item_url(kind, tid),
        "is_pinned": pinned,
    }


def _fetch_hot(cur, exclude_keys, limit):
    """热度聚合：帖子 like+comment*2、视频 view_count，按热度降序。"""
    rows = cur.execute(
        "SELECT 'post' AS kind, id FROM posts WHERE status='visible' ORDER BY (like_count + comment_count * 2) DESC, id DESC LIMIT ?",
        (limit * 2,),
    ).fetchall()
    out = []
    for r in rows:
        key = ("post", r["id"])
        if key in exclude_keys:
            continue
        t = _fetch_target(cur, "post", r["id"])
        if t:
            out.append(_build("post", r["id"], t))
        if len(out) >= limit:
            break
    rows = cur.execute(
        "SELECT id FROM videos WHERE status='approved' ORDER BY view_count DESC, id DESC LIMIT ?",
        (limit * 2,),
    ).fetchall()
    for r in rows:
        key = ("video", r["id"])
        if key in exclude_keys:
            continue
        t = _fetch_target(cur, "video", r["id"])
        if t:
            out.append(_build("video", r["id"], t))
        if len(out) >= limit:
            break
    return out


def _fetch_latest(cur, exclude_keys, limit):
    rows = cur.execute(
        "SELECT 'post' AS kind, id FROM posts WHERE status='visible' ORDER BY id DESC LIMIT ?",
        (limit * 2,),
    ).fetchall()
    out = []
    for r in rows:
        key = ("post", r["id"])
        if key in exclude_keys:
            continue
        t = _fetch_target(cur, "post", r["id"])
        if t:
            out.append(_build("post", r["id"], t))
        if len(out) >= limit:
            break
    return out


def _merge_interspersed(hot, latest, capacity):
    """热度为主、在指定位置穿插最新，去重后返回。"""
    merged = []
    seen = set()
    hi = li = 0
    while len(merged) < capacity and (hi < len(hot) or li < len(latest)):
        if len(merged) in INSERT_POSITIONS and li < len(latest):
            cand = latest[li]
            li += 1
            key = (cand["kind"], cand["target_id"])
            if key in seen:
                continue
            merged.append(cand)
            seen.add(key)
        elif hi < len(hot):
            cand = hot[hi]
            hi += 1
            key = (cand["kind"], cand["target_id"])
            if key in seen:
                continue
            merged.append(cand)
            seen.add(key)
        elif li < len(latest):
            cand = latest[li]
            li += 1
            key = (cand["kind"], cand["target_id"])
            if key in seen:
                continue
            merged.append(cand)
            seen.add(key)
        else:
            break
    return merged


@router.get("/carousel")
def get_carousel():
    now = _now()
    items = []
    pinned_keys = set()
    with db_cursor() as cur:
        rows = cur.execute(
            "SELECT id, item_type, item_id FROM carousel_items "
            "WHERE (start_at IS NULL OR start_at <= ?) AND (end_at IS NULL OR end_at > ?) "
            "ORDER BY sort_order ASC, created_at DESC LIMIT ?",
            (now, now, MAX_ITEMS),
        ).fetchall()
        for row in rows:
            kind, tid = row["item_type"], row["item_id"]
            t = _fetch_target(cur, kind, tid)
            if not t:
                continue
            items.append(_build(kind, tid, t, pinned=True, pinned_id=row["id"]))
            pinned_keys.add((kind, tid))
        capacity = MAX_ITEMS - len(items)
        if capacity > 0:
            hot = _fetch_hot(cur, pinned_keys, capacity)
            latest = _fetch_latest(cur, pinned_keys, min(capacity, LATEST_TAKE))
            items.extend(_merge_interspersed(hot, latest, capacity))
    return {"ok": True, "items": items}


class CarouselUpsertReq(BaseModel):
    item_type: str = Field(..., pattern="^(post|video)$")
    item_id: int = Field(..., gt=0)
    sort_order: int = Field(0, ge=0)
    start_at: str = Field("", max_length=64)
    end_at: str = Field("", max_length=64)


class CarouselUpdateReq(BaseModel):
    sort_order: int = Field(..., ge=0)
    start_at: str = Field("", max_length=64)
    end_at: str = Field("", max_length=64)


@router.post("/admin/carousel")
def upsert_carousel(req: CarouselUpsertReq, user=Depends(require_admin)):
    with db_cursor() as cur:
        t = _fetch_target(cur, req.item_type, req.item_id)
        if not t:
            raise HTTPException(400, "目标不存在或不可用于轮播（帖子需可见、视频需已通过）")
        start_at = req.start_at.strip() or None
        end_at = req.end_at.strip() or None
        existing = cur.execute(
            "SELECT id FROM carousel_items WHERE item_type=? AND item_id=?",
            (req.item_type, req.item_id),
        ).fetchone()
        if existing:
            cur.execute(
                "UPDATE carousel_items SET sort_order=?, start_at=?, end_at=?, created_by=? WHERE id=?",
                (req.sort_order, start_at, end_at, user["id"], existing["id"]),
            )
            return {"ok": True, "id": existing["id"], "updated": True}
        cur.execute(
            "INSERT INTO carousel_items (item_type, item_id, sort_order, start_at, end_at, created_by) "
            "VALUES (?,?,?,?,?,?)",
            (req.item_type, req.item_id, req.sort_order, start_at, end_at, user["id"]),
        )
        return {"ok": True, "id": cur.lastrowid, "updated": False}


@router.delete("/admin/carousel/{item_id}")
def delete_carousel(item_id: int, user=Depends(require_admin)):
    with db_cursor() as cur:
        cur.execute("DELETE FROM carousel_items WHERE id=?", (item_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "置顶项不存在")
    return {"ok": True, "deleted": item_id}


@router.put("/admin/carousel/{item_id}")
def update_carousel(item_id: int, req: CarouselUpdateReq, user=Depends(require_admin)):
    with db_cursor() as cur:
        row = cur.execute("SELECT id FROM carousel_items WHERE id=?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(404, "置顶项不存在")
        cur.execute(
            "UPDATE carousel_items SET sort_order=?, start_at=?, end_at=?, created_by=? WHERE id=?",
            (req.sort_order, req.start_at.strip() or None, req.end_at.strip() or None, user["id"], item_id),
        )
    return {"ok": True, "id": item_id}
