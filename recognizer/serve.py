"""弹幕违规识别服务：FastAPI 封装 improved BERT，输入->预处理->模型->输出"""
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from config import LABEL_MAP, MAX_LEN, MODEL_NAME, OUTPUT_DIR

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="弹幕违规识别服务", version="1.0.0")

# 跨源访问：允许 file:// 或其它端口（如 PyCharm 63342 预览、移动端调试）直接调用接口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=200, description="弹幕文本列表，单条传 [text]")


class PredictResponse(BaseModel):
    results: list[dict]
    latency_ms: float


def load_best_checkpoint(model_name="bert_improved"):
    ckpt_dir = Path(OUTPUT_DIR) / model_name
    best, best_m = None, -1.0
    for c in sorted(ckpt_dir.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1])):
        sp = c / "trainer_state.json"
        if sp.exists():
            import json
            with open(sp, "r", encoding="utf-8") as f:
                st = json.load(f)
            if st.get("best_metric", -1.0) > best_m:
                best_m = st["best_metric"]
                best = st.get("best_model_checkpoint") or str(c)
    if best is None:
        raise FileNotFoundError("未找到最优 checkpoint")
    return best


class DanmakuService:
    def __init__(self, model_name="bert_improved", device=None):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        ckpt = load_best_checkpoint(model_name)
        print(f"[serve] load {ckpt} -> {self.device}", flush=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(ckpt, local_files_only=True).to(self.device).eval()
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, local_files_only=True)
        print("[serve] ready", flush=True)

    @torch.no_grad()
    def predict(self, texts):
        enc = self.tokenizer(
            texts, truncation=True, padding=True, max_length=MAX_LEN, return_tensors="pt"
        ).to(self.device)
        logits = self.model(**enc).logits
        probs = torch.softmax(logits, dim=-1).cpu().numpy()
        preds = probs.argmax(axis=-1)
        results = []
        for t, p, pred in zip(texts, probs, preds):
            top = sorted(zip(LABEL_MAP.values(), p.tolist()), key=lambda x: -x[1])
            results.append({
                "text": t,
                "label": LABEL_MAP[int(pred)],
                "label_id": int(pred),
                "probabilities": {name: round(v, 6) for name, v in top},
            })
        return results


class OnnxService:
    """ONNX Runtime 轻量部署后端（S1-B）：加载 int8 量化模型，CPU 推理，无需 GPU。

    SERVE_BACKEND=onnx 时启用；默认仍走 GPU PyTorch（最低延迟）。
    """

    def __init__(self, model_path=None):
        import onnxruntime as ort
        self.device = "cpu"
        if model_path is None:
            ckpt_dir = Path(OUTPUT_DIR) / "onnx"
            model_path = ckpt_dir / "model_int8.onnx"
            if not model_path.exists():
                model_path = ckpt_dir / "model_fp32.onnx"
            model_path = str(model_path)
        self.model_path = model_path
        self.sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, local_files_only=True)
        print(f"[serve] onnx backend ready: {model_path}", flush=True)

    @torch.no_grad()
    def predict(self, texts):
        import numpy as np
        enc = self.tokenizer(texts, truncation=True, padding=True, max_length=MAX_LEN,
                             return_tensors="np")
        logits = self.sess.run(["logits"], {
            "input_ids": enc["input_ids"].astype(np.int64),
            "attention_mask": enc["attention_mask"].astype(np.int64),
        })[0]
        # log-softmax 稳定版，输出结构与 PyTorch 后端一致
        logits = logits - logits.max(axis=-1, keepdims=True)
        probs = np.exp(logits)
        probs = probs / probs.sum(axis=-1, keepdims=True)
        preds = probs.argmax(axis=-1)
        results = []
        for t, p, pred in zip(texts, probs, preds):
            top = sorted(zip(LABEL_MAP.values(), p.tolist()), key=lambda x: -x[1])
            results.append({
                "text": t,
                "label": LABEL_MAP[int(pred)],
                "label_id": int(pred),
                "probabilities": {name: round(v, 6) for name, v in top},
            })
        return results


# 后端选择：SERVE_BACKEND=onnx 用轻量 CPU 后端，否则 GPU PyTorch
_backend = os.environ.get("SERVE_BACKEND", "torch").lower()
service = OnnxService() if _backend == "onnx" else DanmakuService()


@app.get("/health")
def health():
    return {"status": "ok", "device": str(service.device), "backend": _backend}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    t0 = time.perf_counter()
    results = service.predict(req.texts)
    latency_ms = (time.perf_counter() - t0) * 1000
    return PredictResponse(results=results, latency_ms=round(latency_ms, 3))


# ---------------- 屏幕选区 OCR ----------------
import base64
import threading

import cv2
import numpy as np

OCR_SCORE_THRESH = 0.7      # OCR 置信度下限，低于该值的文本丢弃
OCR_MIN_LEN = 3             # 过短文本（含标点噪声）丢弃


class OcrRequest(BaseModel):
    image: str = Field(..., description="base64 编码的 PNG，允许带 data:image/png;base64, 前缀")


class OcrResponse(BaseModel):
    texts: list[str]
    latency_ms: float
    engine: str = "rapidocr"


class OcrEngineHolder:
    """RapidOCR 懒加载单例；首次调用在子线程完成加载，避免阻塞启动。"""

    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()

    def get(self):
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    t0 = time.perf_counter()
                    from rapidocr_onnxruntime import RapidOCR
                    self._engine = RapidOCR()
                    print(f"[ocr] RapidOCR 引擎就绪 ({(time.perf_counter() - t0):.1f}s)", flush=True)
        return self._engine


ocr_engine = OcrEngineHolder()


def _decode_image(image_b64: str) -> np.ndarray:
    """base64 -> BGR ndarray；兼容 data URL 前缀与 URL-safe 变体。"""
    if "," in image_b64 and image_b64.strip().startswith("data:"):
        image_b64 = image_b64.split(",", 1)[1]
    try:
        raw = base64.b64decode(image_b64)
    except Exception:
        raw = base64.urlsafe_b64decode(image_b64 + "=" * (-len(image_b64) % 4))
    img = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("图片解码失败，请确认传入的是合法 PNG/JPEG 的 base64")
    return img


def _run_ocr(img: np.ndarray) -> list[str]:
    result, _ = ocr_engine.get()(img)
    if not result:
        return []
    texts = []
    for item in result:
        # rapidocr-onnxruntime 1.x 返回 [box, text, score]
        if len(item) < 3:
            continue
        text, score = item[1], item[2]
        text = str(text).strip()
        if text and len(text) >= OCR_MIN_LEN and float(score) >= OCR_SCORE_THRESH:
            texts.append(text)
    return texts


@app.post("/ocr", response_model=OcrResponse)
def ocr(req: OcrRequest):
    t0 = time.perf_counter()
    img = _decode_image(req.image)
    texts = _run_ocr(img)
    latency_ms = (time.perf_counter() - t0) * 1000
    return OcrResponse(texts=texts, latency_ms=round(latency_ms, 3))


# 前端可视化页面（完整演示版）
app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "static"), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("SERVE_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
