"""M6 工程化：集中配置（支持环境变量覆盖，未设置时使用默认值）

配置项与环境变量：
- PLATFORM_PORT          平台后端端口，默认 8080（env: PLATFORM_PORT）
- AUDIT_SERVICE_URL      识别服务基础地址，默认 http://127.0.0.1:8000（env: AUDIT_SERVICE_URL）
- AUDIT_SERVICE_TIMEOUT  识别服务调用超时（秒），默认 5（env: AUDIT_SERVICE_TIMEOUT）
- DICTIONARY_PATH        违规词词典 JSON 路径（env: BADWORD_DICT）
- DATABASE_PATH          数据库文件路径，测试可指向临时库（env: HUPU_DB_PATH）
- LOG_DIR / LOG_FILE     日志目录与文件，默认 backend/logs/platform.log（env: PLATFORM_LOG_DIR）
- LOG_BACKUP_DAYS        日志按天轮转保留天数，默认 7（env: PLATFORM_LOG_BACKUP_DAYS）
"""
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


PLATFORM_PORT = _env_int("PLATFORM_PORT", 8080)
AUDIT_SERVICE_URL = os.environ.get("AUDIT_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
AUDIT_SERVICE_TIMEOUT = _env_float("AUDIT_SERVICE_TIMEOUT", 5.0)
DICTIONARY_PATH = os.environ.get(
    "BADWORD_DICT",
    r"C:\Users\swerey.SWEREY\PycharmProjects\系统\recognizer\badword_variants.json",
)
DATABASE_PATH = os.environ.get("HUPU_DB_PATH", os.path.join(_PROJECT_ROOT, "data", "hupu.db"))
LOG_DIR = os.environ.get("PLATFORM_LOG_DIR", os.path.join(_BACKEND_DIR, "logs"))
LOG_FILE = os.path.join(LOG_DIR, "platform.log")
LOG_BACKUP_DAYS = _env_int("PLATFORM_LOG_BACKUP_DAYS", 7)
# S5 架构优化：uvicorn 多 worker 数（默认 2；SQLite 已开 WAL，支持多进程并发）
PLATFORM_WORKERS = _env_int("PLATFORM_WORKERS", 2)
# S5 日志结构化：文件日志输出 JSON（中文 ensure_ascii=False，便于程序化采集）
LOG_JSON = os.environ.get("PLATFORM_LOG_JSON", "1") == "1"
# S5 热词榜缓存：进程内 TTL 缓存 + 定时刷新（秒）；REDIS_ENABLED=1 时切换到 Redis 后端（需安装 redis 库）
HOTWORD_CACHE_TTL = _env_int("HOTWORD_CACHE_TTL", 60)
HOTWORD_CACHE_REFRESH_INTERVAL = _env_int("HOTWORD_CACHE_REFRESH_INTERVAL", 60)
REDIS_ENABLED = os.environ.get("PLATFORM_REDIS_ENABLED", "0") == "1"
REDIS_URL = os.environ.get("PLATFORM_REDIS_URL", "redis://127.0.0.1:6379/0")
