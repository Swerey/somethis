"""申诉路由：提交申诉 / 我的申诉列表"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db_cursor
from auth import get_current_user_even_banned as get_current_user
from audit_logs import write_audit_log
from models import (
    APPEAL_PENDING,
    SOURCE_POST, SOURCE_COMMENT, SOURCE_VIDEO_COMMENT, SOURCE_DANMAKU,
    SOURCE_VIDEO, SOURCE_LIVE,
)

router = APIRouter(prefix="/api/appeals", tags=["appeals"])

logger = logging.getLogger("audit")

VALID_SOURCES = {
    SOURCE_POST, SOURCE_COMMENT, SOURCE_VIDEO_COMMENT, SOURCE_DANMAKU,
    SOURCE_VIDEO, SOURCE_LIVE,
}


class AppealReq(BaseModel):
    source_type: str = Field(..., max_length=32, description="申诉内容来源类型")
    source_id: int = Field(..., ge=0, description="对应内容 id")
    reason: str = Field(..., min_length=2, max_length=500, description="申诉理由")


@router.post("")
def create_appeal(req: AppealReq, user=Depends(get_current_user)):
    """提交申诉（同一来源内容仅允许一条待处理申诉）"""
    if req.source_type not in VALID_SOURCES:
        raise HTTPException(status_code=400, detail="无效的申诉来源类型")
    with db_cursor() as cur:
        cur.execute(
            "SELECT id FROM appeals WHERE user_id=? AND source_type=? AND source_id=? AND status=?",
            (user["id"], req.source_type, req.source_id, APPEAL_PENDING),
        )
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="该内容已有待处理的申诉")
        cur.execute(
            "INSERT INTO appeals (user_id, source_type, source_id, reason) VALUES (?,?,?,?)",
            (user["id"], req.source_type, req.source_id, req.reason),
        )
        aid = cur.lastrowid
        # M6：申诉提交写审计日志
        write_audit_log(operator_id=user["id"], action="appeal_submit",
                        target_type=req.source_type, target_id=req.source_id,
                        detail=f"提交申诉 appeal_id={aid}", cur=cur)
        logger.info("appeal_submit user_id=%s source_type=%s source_id=%s appeal_id=%s",
                    user["id"], req.source_type, req.source_id, aid)
        cur.execute("SELECT * FROM appeals WHERE id=?", (aid,))
        item = dict(cur.fetchone())
    return {"appeal": item}


@router.get("/me")
def my_appeals(status: str = "", page: int = 1, page_size: int = 20,
               user=Depends(get_current_user)):
    """当前用户申诉列表（可按状态过滤）"""
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    offset = (page - 1) * page_size
    where = "WHERE user_id=?"
    params = [user["id"]]
    if status in ("pending", "approved", "rejected"):
        where += " AND status=?"
        params.append(status)
    with db_cursor() as cur:
        total = cur.execute(f"SELECT COUNT(*) FROM appeals {where}", params).fetchone()[0]
        rows = cur.execute(
            f"""SELECT a.*, u.username, u.nickname FROM appeals a
                JOIN users u ON a.user_id = u.id
                {where} ORDER BY a.id DESC LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        ).fetchall()
    return {"total": total, "page": page, "page_size": page_size, "items": [dict(r) for r in rows]}
