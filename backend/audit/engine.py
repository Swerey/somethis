"""审核引擎：调用识别服务 /predict，带超时与容错兜底"""
import http.client
import json
import threading
import time

from config import AUDIT_SERVICE_URL, AUDIT_SERVICE_TIMEOUT

# M6：识别服务地址集中到 config（默认 http://127.0.0.1:8000）
SERVICE_BASE_URL = AUDIT_SERVICE_URL
SERVICE_PATH = "/predict" if not SERVICE_BASE_URL.endswith("/") else "predict"
SERVICE_URL = SERVICE_BASE_URL + "/predict"
TIMEOUT = AUDIT_SERVICE_TIMEOUT

# 模型调用延迟采样（最近 100 次，供健康度统计）
MODEL_LATENCIES = []

# 长连接：线程局部 HTTPConnection，避免每次调用重建 TCP（S1 推理加速）
_conn_local = threading.local()


def _host_port():
    base = SERVICE_BASE_URL.replace("http://", "").replace("https://", "")
    host, _, port = base.partition(":")
    return host, int(port) if port else 80


def _get_conn():
    conn = getattr(_conn_local, "conn", None)
    if conn is None:
        host, port = _host_port()
        conn = http.client.HTTPConnection(host, port, timeout=TIMEOUT)
        _conn_local.conn = conn
    return conn


def _reset_conn():
    conn = getattr(_conn_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _conn_local.conn = None


def predict(texts: list[str]):
    """调用识别服务批量预测。

    返回 {"results": [...], "latency_ms": ...}；
    服务不可达/超时/异常时返回 None（由 pipeline 做容错兜底）。
    """
    if not texts:
        return None
    payload = json.dumps({"texts": texts}).encode("utf-8")
    conn = _get_conn()
    t0 = time.perf_counter()
    try:
        conn.request("POST", SERVICE_PATH, body=payload,
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        body = resp.read()
        if resp.status != 200:
            _reset_conn()
            return None
        data = json.loads(body.decode("utf-8"))
        data["latency_ms"] = round((time.perf_counter() - t0) * 1000, 3)
        MODEL_LATENCIES.append(data["latency_ms"])
        if len(MODEL_LATENCIES) > 100:
            MODEL_LATENCIES.pop(0)
        return data
    except Exception as exc:
        # 容错：不因识别服务故障导致平台崩溃
        _reset_conn()
        return None


def health() -> bool:
    """探测识别服务是否在线"""
    host, port = _host_port()
    try:
        conn = http.client.HTTPConnection(host, port, timeout=0.5)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        ok = resp.status == 200
        conn.close()
        return ok
    except Exception:
        return False
