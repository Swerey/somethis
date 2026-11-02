"""违规热词榜路由：最近被禁最多的词 Top10 + 拦截量统计

S5：热词榜不再每次请求实时聚合 —— 进程内 TTL 缓存 + 后台定时刷新；
    配置 PLATFORM_REDIS_ENABLED=1 且已安装 redis 库时，自动切换 Redis 缓存后端。
"""
import logging
import threading
import time
from collections import Counter
from datetime import datetime

from fastapi import APIRouter

import config
from db import db_cursor
from audit import rules
from audit.engine import MODEL_LATENCIES

logger = logging.getLogger("audit")
router = APIRouter(prefix="/api/banned-words", tags=["banned-words"])

# ---- S5 缓存层 ----
_mem_cache = {"ts": 0.0, "data": None}
_cache_lock = threading.Lock()
_redis_client = None


def _get_redis():
    global _redis_client
    if not config.REDIS_ENABLED:
        return None
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
            _redis_client.ping()
        except Exception as exc:
            logger.warning("redis_unavailable fallback=memory err=%s", exc)
            _redis_client = None
    return _redis_client


def _cache_key() -> str:
    return "somewhere:banned_words:top:v1"


def _read_cache():
    client = _get_redis()
    if client is not None:
        try:
            raw = client.get(_cache_key())
            if raw:
                import json
                return json.loads(raw), True
        except Exception as exc:
            logger.warning("redis_read_fail err=%s", exc)
    with _cache_lock:
        if _mem_cache["data"] is not None and time.time() - _mem_cache["ts"] < config.HOTWORD_CACHE_TTL:
            return _mem_cache["data"], False
    return None, False


def _write_cache(data):
    client = _get_redis()
    if client is not None:
        try:
            import json
            client.set(_cache_key(), json.dumps(data, ensure_ascii=False),
                       ex=config.HOTWORD_CACHE_TTL * 2)
        except Exception as exc:
            logger.warning("redis_write_fail err=%s", exc)
    with _cache_lock:
        _mem_cache["ts"] = time.time()
        _mem_cache["data"] = data


def _compute_top(limit: int = 10, sample: int = 500) -> dict:
    """聚合计算热词榜（原实时逻辑，提取为独立函数供缓存/定时刷新复用）"""
    rules.load_dictionary()  # 确保词典已加载
    with db_cursor() as cur:
        rows = cur.execute(
            "SELECT content FROM violations ORDER BY id DESC LIMIT ?", (min(sample, 5000),)
        ).fetchall()
        total_violations = cur.execute("SELECT COUNT(*) FROM violations").fetchone()[0]
        today = datetime.now().strftime("%Y-%m-%d 00:00:00")
        today_violations = cur.execute(
            "SELECT COUNT(*) FROM violations WHERE created_at >= ?", (today,)
        ).fetchone()[0]
        high_risk = cur.execute(
            "SELECT COUNT(*) FROM violations WHERE risk_level = 'high'"
        ).fetchone()[0]
        today_posts = cur.execute(
            "SELECT COUNT(*) FROM posts WHERE created_at >= ?", (today,)
        ).fetchone()[0]
        today_comments = cur.execute(
            "SELECT COUNT(*) FROM comments WHERE created_at >= ?", (today,)
        ).fetchone()[0]
        today_danmaku = cur.execute(
            "SELECT COUNT(*) FROM danmaku WHERE created_at >= ?", (today,)
        ).fetchone()[0]
        today_videos = cur.execute(
            "SELECT COUNT(*) FROM videos WHERE created_at >= ?", (today,)
        ).fetchone()[0]

    counter = Counter()
    for row in rows:
        hit = rules.quick_check(row["content"])
        if hit is not None:
            for w in hit[2]:
                counter[w] += 1
    top = [{"word": w, "count": c} for w, c in counter.most_common(min(limit, 50))]

    total_content = today_posts + today_comments + today_danmaku + today_videos
    block_rate = round(today_violations / total_content * 100, 2) if total_content else 0.0
    avg_latency = round(sum(MODEL_LATENCIES) / len(MODEL_LATENCIES), 2) if MODEL_LATENCIES else None

    return {
        "top_words": top,
        "total_violations": total_violations,
        "today_violations": today_violations,
        "high_risk_count": high_risk,
        "block_rate": block_rate,
        "avg_latency_ms": avg_latency,
        "today_content_total": total_content,
        "cached": False,
    }


def _refresh_loop():
    """后台定时刷新：每 HOTWORD_CACHE_REFRESH_INTERVAL 秒预计算一次，避免请求峰值时冷算"""
    while True:
        time.sleep(config.HOTWORD_CACHE_REFRESH_INTERVAL)
        try:
            _write_cache(_compute_top())
            logger.info("banned_words_cache_refreshed ttl=%ss", config.HOTWORD_CACHE_TTL)
        except Exception as exc:
            logger.warning("banned_words_cache_refresh_fail err=%s", exc)


_refresh_thread = threading.Thread(name="hotword-cache-refresh", target=_refresh_loop, daemon=True)
_refresh_thread.start()


def _today_start() -> str:
    return datetime.now().strftime("%Y-%m-%d 00:00:00")


@router.get("/top")
def banned_words_top(limit: int = 10, sample: int = 500):
    """统计最近 sample 条违规记录中命中词典的高频词，返回 Top N 热词榜（TTL 缓存加速）。

    仅统计词典可解释的命中词（规则引擎直接拦截的词）；
    附今日拦截量 / 总拦截量 / 高危数量，供主界面卡片展示。
    """
    cached, from_redis = _read_cache()
    if cached is not None:
        data = dict(cached)
        data["cached"] = True
        data["cache_backend"] = "redis" if from_redis else "memory"
        return data
    data = _compute_top(limit=limit, sample=sample)
    _write_cache(data)
    return data
