"""直播路由：直播间创建/列表/关闭 + WebSocket 实时弹幕（复用审核管线）
批次三增强：直播治理（禁言 mute/unmute、踢出 kick）、WS 弹幕限速、
viewer_count 按 uid 去重实时广播、主播侧在线用户列表（users 广播）。"""
import asyncio
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from db import db_cursor
from auth import get_current_user, decode_token
from audit.pipeline import audit_text, enqueue_review
from models import SOURCE_LIVE, STATUS_BLOCKED

router = APIRouter(prefix="/api/live", tags=["live"])

logger = logging.getLogger("audit")

# room_id -> {uid: {"ws": set[WebSocket], "info": {"username":..., "nickname":...}}}
_room_connections: dict[int, dict[int, dict]] = {}
# room_id -> {"publisher": set[WebSocket], "viewers": set[WebSocket]}
# MJPEG 视频帧转发通道（与弹幕 _room_connections 完全分离）
_video_connections: dict[int, dict] = {}
# uid -> [最近弹幕时间戳]，用于 10s 5 条限速
_rate_bucket: dict[int, list] = defaultdict(list)
RATE_WINDOW = 10.0
RATE_LIMIT = 5


class RoomCreateReq(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    cover: str = ""


class LiveStartReq(BaseModel):
    source_type: str = Field("camera", pattern="^(camera|game)$",
                             description="直播来源：camera=摄像头 / game=游戏画面（屏幕/窗口捕获）")


class LiveMuteReq(BaseModel):
    user_id: int = Field(..., gt=0)
    duration_hours: int = Field(0, ge=0, le=24 * 365, description="禁言时长（小时），0=永久")
    reason: str = Field("", max_length=200)


class LiveKickReq(BaseModel):
    user_id: int = Field(..., gt=0)
    reason: str = Field("", max_length=200)


def _is_room_admin(cur, room_id: int, user: dict) -> bool:
    """主播本人或管理员有权治理直播间"""
    cur.execute("SELECT user_id FROM live_rooms WHERE id=?", (room_id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="直播间不存在")
    return row["user_id"] == user["id"] or user["role"] == "admin"


def _muted_until(cur, room_id: int, uid: int):
    """返回该用户在当前房间的禁言到期时间（None=未禁言；永久=空字符串）"""
    cur.execute(
        """SELECT expires_at FROM live_bans
           WHERE room_id=? AND user_id=? AND ban_type='mute'
             AND (expires_at IS NULL OR expires_at > datetime('now','localtime'))
           ORDER BY id DESC LIMIT 1""",
        (room_id, uid),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return row["expires_at"] or "永久"


def _broadcast(room_id: int, payload: dict):
    for conn in list(_room_connections.get(room_id, {}).values()):
        for ws in list(conn.get("ws", set())):
            try:
                ws.send_json(payload)
            except Exception:
                pass  # 已断开由 disconnect 流程清理


async def _broadcast_async(room_id: int, payload: dict):
    dead = []
    for conn in list(_room_connections.get(room_id, {}).values()):
        for ws in list(conn.get("ws", set())):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
    for ws in dead:
        for conn in _room_connections.get(room_id, {}).values():
            conn["ws"].discard(ws)


def _sync_viewer_count(cur, room_id: int):
    """按 uid 去重的人数写入 DB 并向房间广播 viewers"""
    n = len(_room_connections.get(room_id, {}))
    cur.execute("UPDATE live_rooms SET viewer_count=? WHERE id=?", (n, room_id))
    return n


def _userlist(room_id: int, cur):
    items = []
    with db_cursor() as cur2:
        for uid, conn in _room_connections.get(room_id, {}).items():
            info = conn.get("info", {})
            muted = _muted_until(cur2, room_id, uid)
            items.append({"uid": uid, "username": info.get("username", ""),
                          "nickname": info.get("nickname", ""), "muted": muted is not None})
    return items


@router.post("/rooms")
def create_room(req: RoomCreateReq, user=Depends(get_current_user)):
    """创建直播间（status=live）"""
    with db_cursor() as cur:
        cur.execute(
            """INSERT INTO live_rooms (user_id, title, cover, status, started_at)
               VALUES (?,?,?,?,datetime('now','localtime'))""",
            (user["id"], req.title, req.cover, "live"),
        )
        rid = cur.lastrowid
        cur.execute("SELECT * FROM live_rooms WHERE id=?", (rid,))
        row = dict(cur.fetchone())
    return {"room": row}


@router.get("/rooms")
def list_rooms():
    """直播中房间列表"""
    with db_cursor() as cur:
        rows = cur.execute(
            """SELECT r.*, u.username, u.nickname, u.avatar
               FROM live_rooms r JOIN users u ON r.user_id = u.id
               WHERE r.status='live' ORDER BY r.created_at DESC""",
        ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.get("/rooms/{room_id}")
def get_room(room_id: int):
    """直播间详情（含主播信息与来源类型 stream_type）"""
    with db_cursor() as cur:
        row = cur.execute(
            """SELECT r.*, u.username, u.nickname, u.avatar
               FROM live_rooms r JOIN users u ON r.user_id = u.id
               WHERE r.id=?""",
            (room_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="直播间不存在")
    return {"room": dict(row)}


@router.post("/rooms/{room_id}/start")
def start_room(room_id: int, req: LiveStartReq, user=Depends(get_current_user)):
    """开始直播（主播本人或管理员，幂等）：置 status=live，记录来源类型与开播时间"""
    with db_cursor() as cur:
        _is_room_admin(cur, room_id, user)
        cur.execute(
            """UPDATE live_rooms
               SET status='live', stream_type=?, started_at=COALESCE(started_at, datetime('now','localtime'))
               WHERE id=?""",
            (req.source_type, room_id),
        )
        cur.execute("SELECT * FROM live_rooms WHERE id=?", (room_id,))
        row = dict(cur.fetchone())
    return {"room": row}


def _stop_room_core(room_id: int, user: dict):
    """置直播间为 off 并清理在线连接（主播本人或管理员）"""
    with db_cursor() as cur:
        _is_room_admin(cur, room_id, user)
        cur.execute(
            "UPDATE live_rooms SET status='off', ended_at=datetime('now','localtime') WHERE id=?",
            (room_id,),
        )
        cur.execute("SELECT * FROM live_rooms WHERE id=?", (room_id,))
        row = dict(cur.fetchone())
    _room_connections.pop(room_id, None)
    return row


@router.post("/rooms/{room_id}/stop")
def stop_room(room_id: int, user=Depends(get_current_user)):
    """结束直播（主播本人或管理员）：置 status=off 并清理连接，记录结束时间"""
    return {"room": _stop_room_core(room_id, user)}


@router.post("/rooms/{room_id}/close")
def close_room(room_id: int, user=Depends(get_current_user)):
    """关闭直播间（主播本人或管理员），语义与 stop 一致，保留兼容旧前端"""
    return {"room": _stop_room_core(room_id, user)}


@router.post("/rooms/{room_id}/mute")
async def mute_user(room_id: int, req: LiveMuteReq, user=Depends(get_current_user)):
    """禁言房间内用户（主播本人或管理员），支持期限 expires_at（0=永久）"""
    with db_cursor() as cur:
        _is_room_admin(cur, room_id, user)
        cur.execute("SELECT id, username, nickname FROM users WHERE id=?", (req.user_id,))
        target = cur.fetchone()
        if target is None:
            raise HTTPException(status_code=404, detail="目标用户不存在")
        expires_at = None
        if req.duration_hours > 0:
            expires_at = (datetime.now() + timedelta(hours=req.duration_hours)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """INSERT INTO live_bans (room_id, user_id, ban_type, reason, operator_id, expires_at)
               VALUES (?,?,?,?,?,?)""",
            (room_id, req.user_id, "mute", req.reason, user["id"], expires_at),
        )
        detail = f"禁言用户:{target['username']} 原因:{req.reason or '未填写'} 时长:{req.duration_hours}h"
        cur.execute(
            "INSERT INTO audit_log (operator_id, action, target_type, target_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "live_mute", "live_room", room_id, detail),
        )
        users_items = _userlist(room_id, cur)
    # 若目标在线，立即通知其已被禁言（锁外 await）
    conn = _room_connections.get(room_id, {}).get(req.user_id)
    if conn:
        for ws in list(conn.get("ws", set())):
            try:
                await ws.send_json({"type": "muted", "reason": req.reason or "已被主播禁言",
                                    "until": expires_at or "永久"})
            except Exception:
                pass
    # 刷新主播端用户列表（muted 状态变化）
    await _broadcast_async(room_id, {"type": "users", "items": users_items})
    return {"ok": True, "muted_until": expires_at or "永久"}


@router.post("/rooms/{room_id}/unmute")
async def unmute_user(room_id: int, req: LiveKickReq, user=Depends(get_current_user)):
    """解除房间内用户禁言（主播本人或管理员）"""
    with db_cursor() as cur:
        _is_room_admin(cur, room_id, user)
        cur.execute(
            """DELETE FROM live_bans WHERE room_id=? AND user_id=? AND ban_type='mute'""",
            (room_id, req.user_id),
        )
        cur.execute(
            "INSERT INTO audit_log (operator_id, action, target_type, target_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "live_unmute", "live_room", room_id, f"解禁用户:{req.user_id}"),
        )
        users_items = _userlist(room_id, cur)
    await _broadcast_async(room_id, {"type": "users", "items": users_items})
    logger.info("live_unmute operator=%s room_id=%s target=%s", user["id"], room_id, req.user_id)
    return {"ok": True}


@router.post("/rooms/{room_id}/kick")
async def kick_user(room_id: int, req: LiveKickReq, user=Depends(get_current_user)):
    """踢出房间内用户（主播本人或管理员，仅断开连接，不写禁言）"""
    conn = None
    n_viewers = 0
    users_items = []
    with db_cursor() as cur:
        _is_room_admin(cur, room_id, user)
        cur.execute("SELECT id, username FROM users WHERE id=?", (req.user_id,))
        target = cur.fetchone()
        if target is None:
            raise HTTPException(status_code=404, detail="目标用户不存在")
        conn = _room_connections.get(room_id, {}).pop(req.user_id, None)
        kicked = False
        if conn:
            kicked = True
            _sync_viewer_count(cur, room_id)
            n_viewers = len(_room_connections.get(room_id, {}))
        detail = f"踢出用户:{target['username']} 原因:{req.reason or '未填写'} 在线:{kicked}"
        cur.execute(
            "INSERT INTO audit_log (operator_id, action, target_type, target_id, detail) VALUES (?,?,?,?,?)",
            (user["id"], "live_kick", "live_room", room_id, detail),
        )
        users_items = _userlist(room_id, cur)
    if conn:
        for ws in list(conn.get("ws", set())):
            try:
                await ws.send_json({"type": "kicked", "reason": req.reason or "已被主播移出直播间"})
                await ws.close(code=4403)
            except Exception:
                pass
        await _broadcast_async(room_id, {"type": "viewers", "count": n_viewers})
    await _broadcast_async(room_id, {"type": "users", "items": users_items})
    logger.info("live_kick operator=%s room_id=%s target=%s online=%s", user["id"], room_id, req.user_id, kicked)
    return {"ok": True, "kicked": kicked}


async def _msg_worker(ws: WebSocket, room_id: int, uid: int, queue: asyncio.Queue):
    """后台弹幕处理 worker：审核 -> 入库 -> 广播（FIFO 保序，不阻塞 WS 接收循环）"""
    while True:
        content = await queue.get()
        try:
            audit = await asyncio.to_thread(audit_text, content, uid, SOURCE_LIVE, room_id)
            if audit["status"] == STATUS_BLOCKED:
                await ws.send_json({"type": "blocked", "audit": audit})
                continue
            with db_cursor() as cur:
                cur.execute(
                    "INSERT INTO live_messages (room_id, user_id, content, status) VALUES (?,?,?,?)",
                    (room_id, uid, content, audit["status"]),
                )
                mid = cur.lastrowid
                cur.execute(
                    """SELECT m.id, m.content, m.status, m.created_at, u.nickname, u.username
                       FROM live_messages m JOIN users u ON m.user_id = u.id WHERE m.id=?""",
                    (mid,),
                )
                saved = dict(cur.fetchone())
            if audit.get("needs_review"):
                enqueue_review(SOURCE_LIVE, mid, uid, content,
                               audit.get("review_label", audit.get("label", "")),
                               audit.get("review_risk", "mid"))
                saved["needs_review"] = True
            await _broadcast_async(room_id, {"type": "message", "message": saved})
        except asyncio.CancelledError:
            raise
        except Exception:
            pass


@router.websocket("/{room_id}/ws")
async def live_ws(ws: WebSocket, room_id: int, token: str = ""):
    """直播间实时弹幕通道：接收 -> 禁言校验 -> 限速（接收时刻计数）-> 入队异步审核/入库/广播
    注意：必须先 accept() 再做鉴权/房间校验。若在 accept 前调用 ws.close(code=44xx)，
    Starlette 会在 HTTP 握手阶段直接返回 403，浏览器端拿不到自定义 close code（表现为
    onclose code=1006 / 握手失败），前端无法识别 4401/4404，导致“未登录/房间关闭”被
    误判为网络断连而无效重连（截图中的“连接已断开，重连第5/5次”）。"""
    await ws.accept()
    try:
        payload = decode_token(token)
        uid = int(payload.get("sub", 0))
    except HTTPException:
        await ws.send_json({"type": "error", "code": 4401, "message": "未登录或凭证失效，请重新登录"})
        await ws.close(code=4401)
        return
    with db_cursor() as cur:
        cur.execute("SELECT id FROM live_rooms WHERE id=? AND status='live'", (room_id,))
        if cur.fetchone() is None:
            await ws.send_json({"type": "error", "code": 4404, "message": "直播间不存在或已关闭"})
            await ws.close(code=4404)
            return
        cur.execute("SELECT username, nickname FROM users WHERE id=?", (uid,))
        urow = cur.fetchone()
        if urow is None:
            await ws.send_json({"type": "error", "code": 4401, "message": "用户不存在"})
            await ws.close(code=4401)
            return
        info = {"username": urow["username"], "nickname": urow["nickname"]}
    with db_cursor() as cur:
        cur.execute(
            """SELECT m.id, m.content, m.status, m.created_at, u.nickname, u.username
               FROM live_messages m JOIN users u ON m.user_id = u.id
               WHERE m.room_id=? AND m.status NOT IN ('blocked','banned')
               ORDER BY m.id DESC LIMIT 50""",
            (room_id,),
        )
        rows = cur.fetchall()
        cur.execute(
            "UPDATE live_rooms SET viewer_count = viewer_count + 1 WHERE id=?", (room_id,)
        )
    await ws.send_json({"type": "history", "items": [dict(r) for r in reversed(rows)]})

    room = _room_connections.setdefault(room_id, {})
    if uid not in room:
        room[uid] = {"ws": set(), "info": info}
    room[uid]["ws"].add(ws)

    # 广播：viewers（去重计数）+ users（在线用户列表，供主播面板）
    with db_cursor() as cur:
        n = _sync_viewer_count(cur, room_id)
        cur.execute("SELECT username, nickname FROM users WHERE id=?", (uid,))
        info_row = cur.fetchone()
        if info_row:
            room[uid]["info"] = {"username": info_row["username"], "nickname": info_row["nickname"]}
    await _broadcast_async(room_id, {"type": "viewers", "count": n})
    await _broadcast_async(room_id, {"type": "users", "items": _userlist(room_id, cur)})

    msg_queue: asyncio.Queue = asyncio.Queue()
    worker = asyncio.create_task(_msg_worker(ws, room_id, uid, msg_queue))
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                await ws.send_json({"type": "error", "message": "消息格式错误"})
                continue
            if msg.get("type") != "message" or not msg.get("content"):
                continue
            content = str(msg["content"])[:200].strip()
            if not content:
                continue

            # 禁言校验：命中回 muted，不广播不入库（不计入限速）
            with db_cursor() as cur:
                muted = _muted_until(cur, room_id, uid)
                if muted is not None:
                    await ws.send_json({"type": "muted", "reason": "您已被主播禁言",
                                        "until": muted})
                    continue

            # 限速：接收时刻立即计数（进循环即记录，不受 audit 耗时影响），10 秒窗口内第 6 条直接回
            now = time.time()
            bucket = _rate_bucket[uid]
            while bucket and now - bucket[0] > RATE_WINDOW:
                bucket.pop(0)
            if len(bucket) >= RATE_LIMIT:
                await ws.send_json({"type": "rate_limited", "message": "发送太快，10 秒内最多 5 条弹幕"})
                continue
            bucket.append(now)

            # 审核/入库/广播交给独立 worker 异步处理，不再阻塞接收循环
            await msg_queue.put(content)
    except WebSocketDisconnect:
        pass
    finally:
        worker.cancel()
        try:
            await worker
        except (asyncio.CancelledError, Exception):
            pass
        conn = _room_connections.get(room_id, {}).get(uid)
        if conn:
            conn["ws"].discard(ws)
            if not conn["ws"]:
                _room_connections.get(room_id, {}).pop(uid, None)
                with db_cursor() as cur:
                    n = _sync_viewer_count(cur, room_id)
                await _broadcast_async(room_id, {"type": "viewers", "count": n})
                await _broadcast_async(room_id, {"type": "users", "items": _userlist(room_id, cur)})


@router.websocket("/{room_id}/video/ws")
async def live_video_ws(ws: WebSocket, room_id: int, token: str = ""):
    """MJPEG 帧转发通道：主播截帧推流 -> 观众实时收帧渲染（与弹幕 WS 完全独立）
    鉴权在 accept 之后进行；未登录观众可直接观看（只读），房主连接被标记为 publisher。
    二进制帧仅由 publisher 推流，原样广播给本房间所有 viewer；JSON 控制消息
    (video_start / video_stop) 由 publisher 广播给 viewer，用于观众端画面显隐。"""
    await ws.accept()
    uid = 0
    try:
        payload = decode_token(token)
        uid = int(payload.get("sub", 0))
    except HTTPException:
        uid = 0  # 未登录/凭证失效：降级为匿名观众，允许观看

    is_publisher = False
    with db_cursor() as cur:
        cur.execute("SELECT id, user_id, status FROM live_rooms WHERE id=?", (room_id,))
        row = cur.fetchone()
        if row is None:
            await ws.send_json({"type": "error", "code": 4404, "message": "直播间不存在"})
            await ws.close(code=4404)
            return
        if row["status"] != "live":
            await ws.send_json({"type": "error", "code": 4404, "message": "直播间已关闭"})
            await ws.close(code=4404)
            return
        if uid and row["user_id"] == uid:
            is_publisher = True

    room_v = _video_connections.setdefault(room_id, {"publisher": set(), "viewers": set()})
    if is_publisher:
        room_v["publisher"].add(ws)
    else:
        room_v["viewers"].add(ws)

    try:
        while True:
            try:
                data = await ws.receive()
            except WebSocketDisconnect:
                break
            if data is None:
                break
            if data.get("type") == "websocket.disconnect":
                break
            if data.get("type") != "websocket.receive":
                continue
            raw_bytes = data.get("bytes")
            if raw_bytes is not None:
                # 二进制帧：仅房主(publisher)推流，原样转发给本房间所有观众
                if is_publisher:
                    dead = []
                    for v in list(room_v["viewers"]):
                        try:
                            await v.send_bytes(raw_bytes)
                        except Exception:
                            dead.append(v)
                    for v in dead:
                        room_v["viewers"].discard(v)
                continue
            # 文本帧：JSON 控制消息（video_start / video_stop），仅房主广播给观众
            text = data.get("text") or ""
            if not text:
                continue
            try:
                msg = json.loads(text)
            except Exception:
                continue
            if not is_publisher or msg.get("type") not in ("video_start", "video_stop"):
                continue
            dead = []
            for v in list(room_v["viewers"]):
                try:
                    await v.send_json(msg)
                except Exception:
                    dead.append(v)
            for v in dead:
                room_v["viewers"].discard(v)
    finally:
        if is_publisher:
            room_v["publisher"].discard(ws)
            if not room_v["publisher"]:
                # 主播断开：通知所有观众停止显示画面
                for v in list(room_v["viewers"]):
                    try:
                        await v.send_json({"type": "video_stop"})
                    except Exception:
                        pass
        else:
            room_v["viewers"].discard(ws)
        if not room_v["publisher"] and not room_v["viewers"]:
            _video_connections.pop(room_id, None)
