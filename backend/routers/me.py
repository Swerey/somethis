"""个人中心路由：信用分与流水"""
from datetime import datetime

from fastapi import APIRouter, Depends

from db import db_cursor
from auth import get_current_user_even_banned as get_current_user
from models import CREDIT_DAILY_RECOVER_LIMIT

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("/credits")
def my_credits(user=Depends(get_current_user)):
    """当前用户信用分：今日恢复次数/剩余额度 + 最近信用流水"""
    today = datetime.now().strftime("%Y-%m-%d 00:00:00")
    with db_cursor() as cur:
        cur.execute("SELECT credit_score, status FROM users WHERE id=?", (user["id"],))
        u = dict(cur.fetchone())
        recovered_today = cur.execute(
            "SELECT COUNT(*) FROM credit_log WHERE user_id=? AND delta>0 AND created_at>=?",
            (user["id"], today),
        ).fetchone()[0]
        logs = cur.execute(
            """SELECT id, delta, reason, ref_id, created_at FROM credit_log
               WHERE user_id=? ORDER BY id DESC LIMIT 50""",
            (user["id"],),
        ).fetchall()
    return {
        "credit_score": u["credit_score"],
        "status": u["status"],
        "recovered_today": recovered_today,
        "recover_limit": CREDIT_DAILY_RECOVER_LIMIT,
        "recover_remaining": max(0, CREDIT_DAILY_RECOVER_LIMIT - recovered_today),
        "logs": [dict(r) for r in logs],
    }
