"""屏幕弹幕实时识别辅助工具
截取屏幕指定区域 -> OCR(RapidOCR/ONNX) -> 调用本地识别服务(serve.py /predict) -> 输出违规判定

用法：
  python screen_ocr_tool.py --mode once                # 截全屏识别一次
  python screen_ocr_tool.py --mode once --region 0,700,1920,300   # 截指定区域识别一次
  python screen_ocr_tool.py --mode watch --region 0,700,1920,300  # 循环监控区域，弹幕变化自动识别

前置：识别服务已启动（python serve.py，默认端口 8000）
"""
import argparse
import sys
import time
from collections import deque

import numpy as np
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ANSI 颜色
RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"; CYAN = "\033[96m"; GRAY = "\033[90m"; RESET = "\033[0m"

# 与 config.py 一致的六类
LABELS = ["正常", "色情低俗", "辱骂暴力", "广告引流", "敏感言论", "歧视煽动"]
BAD_COLOR = {0: GREEN, 1: RED, 2: RED, 3: YELLOW, 4: RED, 5: RED}


def parse_region(s):
    """x,y,w,h -> dict"""
    x, y, w, h = [int(v) for v in s.replace("，", ",").split(",")]
    return {"left": x, "top": y, "width": w, "height": h}


def capture(region=None):
    import mss
    with mss.MSS() as sct:
        monitor = region or sct.monitors[1]
        img = np.array(sct.grab(monitor))[:, :, :3]  # BGRA -> BGR
    return img


def frame_changed(prev, cur, thresh):
    if prev is None or prev.shape != cur.shape:
        return True
    diff = np.mean(np.abs(cur.astype(np.int16) - prev.astype(np.int16)))
    return diff > thresh


def ocr(engine, img):
    result, _ = engine(img)
    if not result:
        return []
    return [text for _, text, score in result if score >= 0.7]


class ScreenDanmakuMonitor:
    def __init__(self, server_url, region=None):
        self.server = server_url.rstrip("/")
        self.region = region
        self.engine = None
        self.seen = deque(maxlen=200)          # 已送检文本（去重）
        self.count = 0
        self.violation = 0

    def _ensure_engine(self):
        if self.engine is None:
            from rapidocr_onnxruntime import RapidOCR
            print(f"[init] 加载 OCR 引擎...", flush=True)
            self.engine = RapidOCR()
            print(f"[init] OCR 引擎就绪", flush=True)

    def classify(self, texts):
        if not texts:
            return []
        r = requests.post(f"{self.server}/predict", json={"texts": texts}, timeout=30)
        r.raise_for_status()
        return r.json()["results"]

    def process(self, texts, once=False, min_conf=0.6):
        """OCR 出的文本 -> 过滤已见 -> 送检 -> 打印"""
        texts = [t.strip() for t in texts if t.strip() and len(t.strip()) >= 3]
        new = [t for t in texts if t not in self.seen]
        if not new:
            return
        results = self.classify(new)
        for item in results:
            self.count += 1
            label = item["label"]
            top = item["probabilities"]
            conf = top[label]
            if label != "正常" and conf >= min_conf:
                self.violation += 1
                print(f"{RED}[违规] {item['text']} -> {label} ({conf:.2f}){RESET}", flush=True)
            elif label != "正常":
                print(f"{YELLOW}[存疑] {item['text']} -> {label} ({conf:.2f}){RESET}", flush=True)
            else:
                print(f"{GRAY}[正常] {item['text']} (正常 {conf:.2f}){RESET}", flush=True)
            self.seen.append(item["text"])

    def run_once(self):
        self._ensure_engine()
        print(f"[once] 截取区域: {self.region or '全屏'}", flush=True)
        img = capture(self.region)
        t0 = time.perf_counter()
        texts = ocr(self.engine, img)
        dt = (time.perf_counter() - t0) * 1000
        print(f"[once] OCR {len(texts)} 条文本, 耗时 {dt:.0f}ms", flush=True)
        if texts:
            self.process(texts)
        print(f"\n[CYAN]结果: 识别 {self.count} 条, 违规 {self.violation} 条{RESET}", flush=True)

    def run_watch(self, interval=0.8, thresh=6.0):
        self._ensure_engine()
        print(f"[watch] 监控区域: {self.region or '全屏'} | 轮询 {interval}s | 变化阈值 {thresh}", flush=True)
        print("[watch] 识别服务: " + self.server, flush=True)
        print("[watch] Ctrl+C 停止", flush=True)
        prev = None
        try:
            while True:
                img = capture(self.region)
                if frame_changed(prev, img, thresh):
                    texts = ocr(self.engine, img)
                    self.process(texts)
                    prev = img
                time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n[watch] 停止。本轮识别 {self.count} 条, 违规 {self.violation} 条", flush=True)


def main():
    ap = argparse.ArgumentParser(description="屏幕弹幕实时识别辅助工具")
    ap.add_argument("--mode", choices=["once", "watch"], default="once")
    ap.add_argument("--region", default=None, help="弹幕区域 x,y,w,h，如 0,700,1920,300；缺省全屏")
    ap.add_argument("--server", default="http://127.0.0.1:8000", help="识别服务地址")
    ap.add_argument("--interval", type=float, default=0.8, help="watch 轮询间隔（秒）")
    ap.add_argument("--thresh", type=float, default=6.0, help="画面变化触发阈值（像素均值差）")
    args = ap.parse_args()

    region = parse_region(args.region) if args.region else None
    m = ScreenDanmakuMonitor(args.server, region)
    if args.mode == "once":
        m.run_once()
    else:
        m.run_watch(args.interval, args.thresh)


if __name__ == "__main__":
    main()
