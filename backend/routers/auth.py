"""认证路由：注册 / 登录 / 当前用户"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db_cursor
from auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterReq(BaseModel):
    username: str = Field(..., min_length=2, max_length=32, description="用户名")
    password: str = Field(..., min_length=6, max_length=64, description="密码")
    nickname: str = Field("", max_length=32, description="昵称")
    phone: str = Field("", max_length=20, description="手机号")


class LoginReq(BaseModel):
    username: str = Field(..., max_length=32)
    password: str = Field(..., max_length=64)


def _user_payload(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "nickname": user["nickname"],
        "avatar": user["avatar"],
        "credit_score": user["credit_score"],
        "role": user["role"],
        "created_at": user["created_at"],
    }


@router.post("/register")
def register(req: RegisterReq):
    with db_cursor() as cur:
        cur.execute("SELECT id FROM users WHERE username=?", (req.username,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="用户名已存在")
        nickname = req.nickname or req.username
        cur.execute(
            "INSERT INTO users (username, password_hash, nickname, phone) VALUES (?,?,?,?)",
            (req.username, hash_password(req.password), nickname, req.phone.strip()),
        )
        uid = cur.lastrowid
        cur.execute("SELECT * FROM users WHERE id=?", (uid,))
        user = dict(cur.fetchone())
    token = create_token(user["id"], user["username"], user["role"])
    return {"token": token, "user": _user_payload(user)}


@router.post("/login")
def login(req: LoginReq):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE username=?", (req.username,))
        row = cur.fetchone()
    if row is None or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    user = dict(row)
    token = create_token(user["id"], user["username"], user["role"])
    return {"token": token, "user": _user_payload(user)}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return {"user": _user_payload(user)}
