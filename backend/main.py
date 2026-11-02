"""虎扑式综合交流平台 - 后端入口
启动：python main.py （默认端口 8080，默认 2 worker）
依赖识别服务：先启动 training/serve.py（端口 8000）提供 /predict 审核
"""
import json
import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import TimedRotatingFileHandler

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Match, Mount
from starlette.staticfiles import StaticFiles

import config
from db import init_db, BASE_DIR
from routers import auth as auth_router
from routers import videos as videos_router
from routers import posts as posts_router
from routers import danmaku as danmaku_router
from routers import admin as admin_router
from routers import banned_words as banned_words_router
from routers import live as live_router
from routers import me as me_router
from routers import appeals as appeals_router
from routers import users as users_router
from routers import reports as reports_router
from routers import carousel as carousel_router


class JsonFormatter(logging.Formatter):
    """S5 日志结构化：JSON 单行输出（中文 ensure_ascii=False，便于论文性能数据采集）"""

    def format(self, record):
        payload = {
            "ts": self.formatTime(record, self.datefmt or "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    """M6 日志：控制台 + 文件 logs/platform.log（按天轮转，保留 LOG_BACKUP_DAYS 天）。

    S5：文件日志默认输出 JSON 结构化；控制台保留人类可读文本便于开发调试。
    """
    os.makedirs(config.LOG_DIR, exist_ok=True)
    text_fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler = TimedRotatingFileHandler(
        config.LOG_FILE, when="midnight", backupCount=config.LOG_BACKUP_DAYS, encoding="utf-8"
    )
    file_handler.setFormatter(JsonFormatter() if config.LOG_JSON else text_fmt)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(text_fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    # audit 子 logger（pipeline/admin/live 等）挂到同一处理器，inherit root handlers
    logging.getLogger("audit").setLevel(logging.INFO)


setup_logging()


class WsAwareMount(Mount):
    """静态资源挂载：显式跳过 WebSocket scope，避免抢占 /api 下的 WS 路由"""

    def matches(self, scope):
        if scope["type"] == "websocket":
            return Match.NONE, {}
        return super().matches(scope)


class CachedStaticFiles(StaticFiles):
    """批次B-2：静态资源 Cache-Control
    - 版本化资源（.css/.js/.svg/.png/.jpg 等，经 ?v= 参数引用）：max-age=604800 长缓存
    - HTML 页面：no-cache（页面内容随版本升级变化，浏览器需回源校验）"""

    def file_response(self, full_path, stat_result, scope, status_code=200):
        resp = super().file_response(full_path, stat_result, scope, status_code)
        p = scope.get("path", "").lower()
        if p.endswith((".html", ".htm")):
            resp.headers["Cache-Control"] = "no-cache"
        else:
            resp.headers["Cache-Control"] = "public, max-age=604800"
        return resp


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库并执行存疑队列超时自动折叠（T11）"""
    init_db()
    from audit.pipeline import auto_fold_expired
    folded = auto_fold_expired(24)
    logging.getLogger("audit").info("lifespan init_db ok, auto_fold_expired folded=%s", folded)
    yield


app = FastAPI(
    title="虎扑式综合交流平台",
    version="0.1.0",
    description="弹幕违规识别驱动的社区内容审核骨架",
    lifespan=lifespan,
)

# 跨域：允许本地前端调试
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 前端静态资源（根目录 /static，访问 http://127.0.0.1:8080/）
# 必须放在所有 API 路由之后注册：
# - HTTP 按注册顺序正向匹配，_IncludedRouter 先于 Mount，/api 不会被静态抢占
# - WebSocket 反向匹配，WsAwareMount 对 ws scope 返回 NONE，同样不会抢占 /api 下的 WS
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")


@app.get("/api/health")
def health():
    from audit.engine import health as svc_health
    return {
        "status": "ok",
        "audit_service": "online" if svc_health() else "offline",
        "docs": "/docs",
    }


# 注册路由
app.include_router(auth_router.router)
app.include_router(videos_router.router)
app.include_router(posts_router.router)
app.include_router(danmaku_router.router)
app.include_router(admin_router.router)
app.include_router(banned_words_router.router)
app.include_router(live_router.router)
app.include_router(me_router.router)
app.include_router(appeals_router.router)
app.include_router(users_router.router)
app.include_router(reports_router.router)
app.include_router(carousel_router.router)

if os.path.isdir(STATIC_DIR):
    app.router.routes.append(
        WsAwareMount("/", app=CachedStaticFiles(directory=STATIC_DIR, html=True), name="static")
    )


if __name__ == "__main__":
    # Windows 下 uvicorn 多 worker 会通过 socket.share/fromshare 共享同一监听 socket，
    # 每个 worker 在 asyncio create_server 时都会对同一 socket 调用 sock.listen()，
    # Windows 上同一 socket 第二次 listen 返回 WSAEINVAL，即 OSError: [WinError 10022]，
    # 表现为子进程崩溃重启（"Child process died"）。因此 Windows 上固定单 worker 启动；
    # 需要提升并发时可部署多实例 + 前置负载均衡（如 nginx），而非依赖 uvicorn 多 worker。
    uvicorn.run("main:app", host="0.0.0.0", port=config.PLATFORM_PORT, log_level="info")
