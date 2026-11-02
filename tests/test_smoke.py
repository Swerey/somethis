# -*- coding: utf-8 -*-
"""M6 工程化 - 冒烟测试（使用临时测试库，不污染 data/hupu.db）

覆盖 4 条最小链路：
1. 注册登录
2. 发帖拦截（词典命中 -> blocked + dict_block 审计）
3. 存疑上报（模型判中危 -> visible + review_queue + review_enqueue 审计）
4. 审核处置（管理员确认违规 -> resolved + violations + review_ban 审计）

运行方式（项目根目录）：
    pip install pytest httpx
    python -m pytest tests/test_smoke.py -v
"""
import os
import sys
import tempfile

import pytest

# ---- 必须先于任何 backend 模块导入：HUPU_DB_PATH 指向临时库 ----
_TMP_DIR = tempfile.mkdtemp(prefix="hupu_smoke_")
os.environ["HUPU_DB_PATH"] = os.path.join(_TMP_DIR, "smoke.db")

_BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from db import init_db, db_cursor  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import main as app_main  # noqa: E402
from audit import engine, rules  # noqa: E402

init_db()

# 模块级共享状态：普通用户 token / admin token / 存疑条目 id
_STATE = {"user_token": None, "admin_token": None, "queue_id": None}


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app_main.app) as c:
        yield c


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _register_login(client, username, password, nickname):
    r = client.post("/api/auth/register", json={
        "username": username, "password": password, "nickname": nickname,
    })
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    r2 = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r2.status_code == 200, r2.text
    return r2.json()["token"]


def _db_exec(sql, params=()):
    with db_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def _audit_count(action, target_type=None, target_id=None):
    sql = "SELECT COUNT(*) AS n FROM audit_log WHERE action=?"
    params = [action]
    if target_type:
        sql += " AND target_type=?"
        params.append(target_type)
    if target_id:
        sql += " AND target_id=?"
        params.append(target_id)
    return _db_exec(sql, params)[0]["n"]


# ---------- 1. 注册登录 ----------
def test_register_login(client):
    _STATE["user_token"] = _register_login(
        client, "smoke_user", "smoke123", "冒烟用户"
    )
    # 管理端链路使用内置管理员账号 admin/admin123（注册接口不产生 admin 角色）
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    _STATE["admin_token"] = r.json()["token"]
    # 校验注册/登录后能取到当前用户
    r = client.get("/api/auth/me", headers=_auth(_STATE["user_token"]))
    assert r.status_code == 200
    assert r.json()["user"]["username"] == "smoke_user"


# ---------- 2. 发帖拦截（词典命中） ----------
def test_post_dict_block(client):
    # 2.1 管理员维护一条高危险违规词，reload 后立即生效
    r = client.post("/api/admin/banned_words", headers=_auth(_STATE["admin_token"]), json={
        "word": "冒烟拦截词xyz", "category": "敏感言论", "risk_level": "high",
    })
    assert r.status_code == 200, r.text
    rules.reload_dictionary()
    hit = rules.quick_check("冒烟拦截词xyz")
    assert hit is not None and hit[1] == "high"

    # 2.2 普通用户发帖含违规词 -> 400 拦截
    before = _audit_count("dict_block")
    r = client.post("/api/posts", headers=_auth(_STATE["user_token"]), json={
        "title": "测试", "content": "这是一条包含冒烟拦截词xyz的内容", "category": "闲聊",
    })
    assert r.status_code == 400, r.text

    # 2.3 落库校验：违规记录 + 审计日志
    viols = _db_exec(
        "SELECT COUNT(*) AS n FROM violations WHERE content LIKE ?", ("%冒烟拦截词xyz%",)
    )
    assert viols[0]["n"] >= 1
    assert _audit_count("dict_block") > before


# ---------- 3. 存疑上报（模型判中危 -> 放行 + 入队列） ----------
def test_enqueue_review(client, monkeypatch):
    # 3.1 mock 识别服务：判定为「辱骂暴力」但置信度不足 -> 中危存疑
    def fake_predict(texts):
        return {
            "results": [{
                "label": "辱骂暴力",
                "probabilities": {"辱骂暴力": 0.70, "正常": 0.30},
            }],
            "latency_ms": 8,
        }

    monkeypatch.setattr(engine, "predict", fake_predict)
    before_q = _db_exec("SELECT COUNT(*) AS n FROM review_queue")[0]["n"]
    before_audit = _audit_count("review_enqueue")

    r = client.post("/api/posts", headers=_auth(_STATE["user_token"]), json={
        "title": "存疑测试", "content": "这是一条疑似违规但未达拦截阈值的内容", "category": "闲聊",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["post"]["status"] == "visible"
    assert body["audit"].get("needs_review") is True

    # 3.2 队列与审计校验
    after_q = _db_exec("SELECT COUNT(*) AS n FROM review_queue")[0]["n"]
    assert after_q == before_q + 1
    assert _audit_count("review_enqueue") > before_audit
    _STATE["queue_id"] = _db_exec(
        "SELECT id FROM review_queue ORDER BY id DESC LIMIT 1"
    )[0]["id"]


# ---------- 4. 审核处置（管理员确认违规） ----------
def test_review_dispose(client):
    qid = _STATE["queue_id"]
    assert qid is not None, "前置链路未产生存疑条目"

    # 4.1 管理员列表可见该条目
    r = client.get("/api/admin/reviews?status=pending&page=1&page_size=50",
                   headers=_auth(_STATE["admin_token"]))
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(it["id"] == qid for it in items), "存疑条目不在待审列表"

    # 4.2 确认违规 -> ban
    r = client.post(f"/api/admin/reviews/{qid}/ban", headers=_auth(_STATE["admin_token"]))
    assert r.status_code == 200, r.text

    # 4.3 落库校验：队列 resolved + violations banned + 审计 review_ban
    row = _db_exec("SELECT status, action, user_id, source_id FROM review_queue WHERE id=?", (qid,))[0]
    assert row["status"] == "resolved" and row["action"] == "ban"
    assert _audit_count("review_ban") >= 1
    banned = _db_exec(
        "SELECT COUNT(*) AS n FROM violations WHERE action='banned' AND user_id=?",
        (row["user_id"],),
    )[0]["n"]
    assert banned >= 1, "确认违规后应写入 violations(action=banned)"

    # 4.4 审计日志查询接口可读到本次处置
    r = client.get("/api/admin/audit-logs?action=review_ban&page=1&page_size=20",
                   headers=_auth(_STATE["admin_token"]))
    assert r.status_code == 200
    assert r.json()["total"] >= 1


# ---------- 5. 批次三：鉴权全覆盖抽查 ----------
def test_auth_required(client):
    # 5.1 未带 token 访问上传 -> 401
    r = client.post("/api/videos/upload", files={"file": ("a.mp4", b"x" * 10, "video/mp4")})
    assert r.status_code == 401, r.text
    # 5.2 未带 token 访问管理端接口 -> 401
    r = client.get("/api/admin/videos/review")
    assert r.status_code == 401, r.text
    r = client.get("/api/admin/reviews?status=pending")
    assert r.status_code == 401, r.text
    r = client.get("/api/admin/users")
    assert r.status_code == 401, r.text
    # 5.3 普通用户访问管理端接口 -> 403
    r = client.get("/api/admin/videos/review", headers=_auth(_STATE["user_token"]))
    assert r.status_code == 403, r.text


# ---------- 6. 批次三：上传 MIME 二次校验 ----------
def test_upload_mime_guard(client):
    # 6.1 视频伪装：扩展名 mp4 但 content_type 非视频 -> 400
    r = client.post("/api/videos/upload", headers=_auth(_STATE["user_token"]),
                    files={"file": ("evil.mp4", b"MZ" * 100, "application/x-msdownload")},
                    data={"title": "伪装视频"})
    assert r.status_code == 400, r.text
    assert "内容类型" in r.text or "MIME" in r.text

    # 6.2 封面伪装：png 扩展名但 content_type 为 text/plain -> 400
    r = client.post("/api/videos/upload", headers=_auth(_STATE["user_token"]),
                    files={
                        "file": ("ok.mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 512, "video/mp4"),
                        "cover": ("fake.png", b"plain text not image", "text/plain"),
                    },
                    data={"title": "封面伪装"})
    assert r.status_code == 400, r.text
    assert "封面内容类型校验失败" in r.text


# ---------- 7. 批次三：封面大小校验 ----------
def test_upload_cover_too_large(client):
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (10 * 1024 * 1024 + 1024)  # >10MB
    r = client.post("/api/videos/upload", headers=_auth(_STATE["user_token"]),
                    files={
                        "file": ("ok.mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 512, "video/mp4"),
                        "cover": ("big.png", big, "image/png"),
                    },
                    data={"title": "超大封面"})
    assert r.status_code == 400, r.text
    assert "封面超过 10MB 上限" in r.text


# ---------- 8. 批次三：正常上传生成缩略图 ----------
def test_upload_thumbnail(client, monkeypatch):
    def fake_predict(texts):
        return {"results": [{"label": "正常", "probabilities": {"正常": 0.95, "辱骂暴力": 0.05}}],
                "latency_ms": 5}

    monkeypatch.setattr(engine, "predict", fake_predict)
    from PIL import Image
    import io as _io
    from db import BASE_DIR
    _STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")

    buf = _io.BytesIO()
    Image.new("RGB", (800, 450), (30, 144, 255)).save(buf, "PNG")
    png_bytes = buf.getvalue()

    r = client.post("/api/videos/upload", headers=_auth(_STATE["user_token"]),
                    files={
                        "file": ("demo.mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 1024, "video/mp4"),
                        "cover": ("cover_demo.png", png_bytes, "image/png"),
                    },
                    data={"title": "缩略图测试视频", "description": "批次三缩略图验证"})
    assert r.status_code == 200, r.text
    body = r.json()["video"]
    assert body["thumb_url"] and body["thumb_url"].startswith("/uploads/covers/thumbs/")
    # 缩略图文件真实存在
    thumb_disk = os.path.join(_STATIC_DIR, body["thumb_url"].lstrip("/"))
    assert os.path.exists(thumb_disk), "缩略图文件未落盘"
    # 缩略图宽度为 THUMB_WIDTH(360)
    with Image.open(thumb_disk) as im:
        assert im.width == 360, f"缩略图宽度 {im.width} != 360"

    # 列表接口返回 thumb_url（先管理员审核通过，pending 不进公开列表）
    r = client.post(f"/api/admin/videos/{body['id']}/review",
                    headers=_auth(_STATE["admin_token"]), json={"action": "approve"})
    assert r.status_code == 200, r.text
    r = client.get("/api/videos?page=1&page_size=50")
    assert r.status_code == 200
    item = next((it for it in r.json()["items"] if it["id"] == body["id"]), None)
    assert item is not None and item["thumb_url"] == body["thumb_url"]

    # 清理测试上传的视频/封面/缩略图文件
    _cleanup_upload(body, _STATIC_DIR)


def _cleanup_upload(video_row, _STATIC_DIR):
    for rel in [video_row.get("url", ""), video_row.get("cover_url", ""),
                video_row.get("thumb_url", "")]:
        if not rel:
            continue
        disk = os.path.join(_STATIC_DIR, rel.lstrip("/"))
        if os.path.exists(disk):
            os.remove(disk)
