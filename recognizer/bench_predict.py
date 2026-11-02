# -*- coding: utf-8 -*-
"""S4-A：识别服务并发压测（/predict，ONNX/GPU 后端按服务当前配置）

- 测试负载：从 test.jsonl 抽取真实弹幕文本，批量 8 条/请求（模拟审核批量）
- 并发档位：1 / 8 / 16 / 32 / 64
- 指标：TPS、P50/P95/P99 延迟
- 产出：recognizer/outputs/eval/bench_report.json + bench_report.md

用法：python recognizer/bench_predict.py
"""
import json
import os
import statistics
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
EVAL_DIR = Path(BASE_DIR) / "outputs" / "eval"
EVAL_DIR.mkdir(parents=True, exist_ok=True)

TEST_SET = r"C:\Users\swerey.SWEREY\PycharmProjects\系统\datasets\processed_v2\test.jsonl"
URL = "http://127.0.0.1:8000/predict"
BATCH = 8          # 每请求弹幕条数（贴近实时批量审核）
REQS = 200         # 每并发档总请求数
CONCURRENCIES = [1, 8, 16, 32, 64]


def load_sample(n=200):
    texts = []
    with open(TEST_SET, "r", encoding="utf-8") as f:
        for line in f:
            o = json.loads(line.strip())
            texts.append(o["text"])
            if len(texts) >= n * BATCH:
                break
    return texts


def call_once(payload):
    req = urllib.request.Request(URL, data=payload.encode(),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()
    return None


def bench(concurrency, payloads):
    lat = []
    done = 0
    lock = __import__("threading").Lock()

    def worker():
        nonlocal done
        while True:
            with lock:
                if done >= len(payloads):
                    return
                idx = done
                done += 1
            t0 = time.perf_counter()
            call_once(payloads[idx])
            lat.append((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(worker) for _ in range(concurrency)]
        for f in futures:
            f.result()
    total = time.perf_counter() - t0
    tps = len(payloads) * BATCH / total
    lat.sort()
    p50 = lat[int(len(lat) * 0.50)]
    p95 = lat[int(len(lat) * 0.95)]
    p99 = lat[int(len(lat) * 0.99)]
    return {
        "concurrency": concurrency,
        "requests": len(payloads),
        "texts": len(payloads) * BATCH,
        "tps": round(tps, 1),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "elapsed_s": round(total, 2),
    }


def main():
    print("[bench] 抽取测试弹幕")
    texts = load_sample()
    payloads = [json.dumps({"texts": texts[i:i + BATCH]}, ensure_ascii=False)
                for i in range(0, len(texts), BATCH)]
    print(f"[bench] {len(texts)} 条弹幕, {len(payloads)} 个批量请求")

    # 预热
    print("[bench] 预热 20 请求")
    for p in payloads[:20]:
        call_once(p)

    rows = []
    for c in CONCURRENCIES:
        print(f"[bench] 并发={c}")
        rows.append(bench(c, payloads))
        time.sleep(1)

    report = {"service": URL, "batch": BATCH, "results": rows}
    (EVAL_DIR / "bench_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# 识别服务并发压测报告（S4-A）", "",
          f"- 服务：`{URL}`（批量 {BATCH} 条/请求）",
          f"- 测试文本：从 test.jsonl 抽取真实弹幕 {len(texts)} 条", "",
          "| 并发 | 请求数 | 弹幕数 | TPS(条/s) | P50(ms) | P95(ms) | P99(ms) | 总耗时(s) |",
          "|------|--------|--------|-----------|---------|---------|---------|-----------|"]
    for r in rows:
        md.append(f"| {r['concurrency']} | {r['requests']} | {r['texts']} | {r['tps']} "
                  f"| {r['p50_ms']} | {r['p95_ms']} | {r['p99_ms']} | {r['elapsed_s']} |")
    md.append("")
    (EVAL_DIR / "bench_report.md").write_text("\n".join(md), encoding="utf-8")
    print(f"[bench] 报告已写入 {EVAL_DIR / 'bench_report.md'}")


if __name__ == "__main__":
    main()
