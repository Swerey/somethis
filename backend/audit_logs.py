"""审计日志写入辅助：统一 audit_log 表写入入口（供审核管线 / 管理端 / 直播治理复用）"""
from db import db_cursor

# 系统自动处置（模型拦截 / 词典拦截 / 存疑上报 / 自动折叠 / 自动封禁）操作者视为系统
SYSTEM_OPERATOR = 0


def write_audit_log(operator_id: int = SYSTEM_OPERATOR, action: str = "",
                    target_type: str = "", target_id: int = 0,
                    detail: str = "", cur=None) -> int:
    """写入一条审计日志并返回日志 id。

    cur 可选：传入外层游标/连接时复用同一连接（避免嵌套 db_cursor 自死锁）；
    未传时自行开启新连接。
    """
    sql = ("INSERT INTO audit_log (operator_id, action, target_type, target_id, detail) "
           "VALUES (?,?,?,?,?)")
    params = (operator_id, action, target_type, target_id, detail)
    if cur is not None:
        c = cur if hasattr(cur, "execute") else cur.cursor()
        c.execute(sql, params)
        return c.lastrowid
    with db_cursor() as c:
        c.execute(sql, params)
        return c.lastrowid
