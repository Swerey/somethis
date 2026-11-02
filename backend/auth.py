"""认证模块：注册/登录/JWT 签发与鉴权依赖"""
import hashlib
import os
import secrets
import time

import jwt
from fastapi import Depends, HTTPException, Header

from db import db_cursor, DATA_DIR

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_SECONDS = 7 * 24 * 3600  # 7 天

_SECRET_FILE = os.path.join(DATA_DIR, "jwt_secret.txt")


def _load_secret() -> str:
    """读取或生成持久化 JWT 密钥（重启不失效）"""
    os.makedirs(os.path.dirname(_SECRET_FILE), exist_ok=True)
    if os.path.exists(_SECRET_FILE):
        with open(_SECRET_FILE, "r", encoding="utf-8") as f:
            s = f.read().strip()
            if s:
                return s
    s = secrets.token_hex(32)
    with open(_SECRET_FILE, "w", encoding="utf-8") as f:
        f.write(s)
    return s


JWT_SECRET = _load_secret()


def hash_password(password: str, salt: str = None) -> str:
    """PBKDF2-SHA256 密码哈希（标准库，无 bcrypt 依赖）"""
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except Exception:
        return False
    return secrets.compare_digest(hash_password(password, salt), stored)


def create_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": int(time.time()) + JWT_EXPIRE_SECONDS,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """解码 JWT，失败抛 HTTPException 401"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except Exception:
        raise HTTPException(status_code=401, detail="无效的登录凭证")


def get_current_user(authorization: str = Header(default="")):
    """FastAPI 依赖：从 Authorization: Bearer xxx 解析当前用户"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:].strip()
    payload = decode_token(token)
    uid = int(payload.get("sub", 0))
    with db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id=?", (uid,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    user = dict(row)
    if user.get("status") == "banned":
        raise HTTPException(status_code=403, detail="账号已被封禁")
    return user


def get_current_user_even_banned(authorization: str = Header(default="")):
    """FastAPI 依赖：解析当前用户，不因封禁拒绝（用于申诉等封禁期仍可用的只读/申诉能力）"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:].strip()
    payload = decode_token(token)
    uid = int(payload.get("sub", 0))
    with db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id=?", (uid,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return dict(row)


def require_admin(user=Depends(get_current_user)):
    """FastAPI 依赖：仅管理员可访问"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
