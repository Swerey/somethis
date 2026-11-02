"""S1-B：导出 BERT 最优 checkpoint 为 ONNX（fp32 全精度 + int8 动态量化），供轻量化部署对比。

用法（在 recognizer 环境 torch_gpu 下运行）：
    python recognizer/export_onnx.py

产出：
    outputs/onnx/model_fp32.onnx      全精度（动态轴 batch/seq）
    outputs/onnx/model_int8.onnx      动态量化 int8（权重压缩约 4 倍）
    outputs/onnx/export_report.json   导出与验证摘要
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from config import LABEL_MAP, MAX_LEN, MODEL_NAME, OUTPUT_DIR


def load_best_checkpoint(model_name="bert_improved"):
    ckpt_dir = Path(OUTPUT_DIR) / model_name
    best, best_m = None, -1.0
    for c in sorted(ckpt_dir.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1])):
        sp = c / "trainer_state.json"
        if sp.exists():
            st = json.loads(sp.read_text(encoding="utf-8"))
            if st.get("best_metric", -1.0) > best_m:
                best_m = st["best_metric"]
                best = st.get("best_model_checkpoint") or str(c)
    if best is None:
        raise FileNotFoundError("未找到最优 checkpoint")
    return best


def main():
    out_dir = Path(OUTPUT_DIR) / "onnx"
    out_dir.mkdir(parents=True, exist_ok=True)
    # onnxruntime 量化对含中文路径支持不佳：中间文件先放英文工作目录，完成后复制回产出目录
    work_dir = Path(os.environ.get("ONNX_WORK_DIR", str(out_dir)))
    work_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    ckpt = load_best_checkpoint()
    print(f"[export] load {ckpt}")
    model = AutoModelForSequenceClassification.from_pretrained(ckpt, local_files_only=True).eval()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, local_files_only=True)

    # 动态轴导出（batch、seq 均可变）
    dummy = tokenizer(["测试弹幕"], truncation=True, padding=True, max_length=MAX_LEN,
                      return_tensors="pt")
    dynamic_axes = {
        "input_ids": {0: "batch", 1: "seq"},
        "attention_mask": {0: "batch", 1: "seq"},
        "logits": {0: "batch"},
    }
    fp32_work = str(work_dir / "model_fp32.onnx")
    torch.onnx.export(
        model,
        (dummy["input_ids"], dummy["attention_mask"]),
        fp32_work,
        input_names=["input_ids", "attention_mask"],
        output_names=["logits"],
        dynamic_axes=dynamic_axes,
        opset_version=17,
        do_constant_folding=True,
    )
    print(f"[export] fp32 done ({time.perf_counter()-t0:.1f}s) -> {fp32_work}")

    # int8 动态量化（weight-only，兼容 CPU/GPU 部署）
    int8_work = None
    try:
        from onnxruntime.quantization import quantize_dynamic, QuantType
        int8_work = str(work_dir / "model_int8.onnx")
        quantize_dynamic(fp32_work, int8_work, weight_type=QuantType.QInt8)
        print(f"[export] int8 done -> {int8_work}")
    except Exception as e:
        print(f"[export] int8 量化跳过: {e}")
        int8_work = None

    # 复制回项目产出目录
    import shutil
    fp32_path = str(out_dir / "model_fp32.onnx")
    int8_path = str(out_dir / "model_int8.onnx") if int8_work else None
    shutil.copyfile(fp32_work, fp32_path)
    if int8_work:
        shutil.copyfile(int8_work, int8_path)

    # 验证：onnxruntime 推理一致性 + 延迟
    import numpy as np
    import onnxruntime as ort

    report = {"checkpoint": ckpt, "fp32": fp32_path, "int8": int8_path, "latency": {}}
    samples = ["主播唱得不错", "加微信领红包", "傻逼滚出直播间", "今天天气真好啊", "666666"]
    enc = tokenizer(samples, truncation=True, padding=True, max_length=MAX_LEN, return_tensors="np")
    feeds = {"input_ids": enc["input_ids"].astype(np.int64),
             "attention_mask": enc["attention_mask"].astype(np.int64)}

    for name, path in [("fp32", fp32_path), ("int8", int8_path)]:
        if not path:
            continue
        sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        lat = []
        for _ in range(30):
            t1 = time.perf_counter()
            logits = sess.run(["logits"], feeds)[0]
            lat.append((time.perf_counter() - t1) * 1000)
        preds = logits.argmax(axis=-1)
        report["latency"][name] = {
            "avg_ms": round(sum(lat) / len(lat), 2),
            "min_ms": round(min(lat), 2),
            "labels": [LABEL_MAP[int(p)] for p in preds],
        }
        print(f"[verify] {name}: avg={report['latency'][name]['avg_ms']}ms labels={report['latency'][name]['labels']}")

    # PyTorch CPU 对照
    model.to("cpu")
    with torch.no_grad():
        enc_t = tokenizer(samples, truncation=True, padding=True, max_length=MAX_LEN,
                          return_tensors="pt")
        lat = []
        for _ in range(30):
            t1 = time.perf_counter()
            model(**enc_t)
            lat.append((time.perf_counter() - t1) * 1000)
        report["latency"]["torch_cpu"] = {
            "avg_ms": round(sum(lat) / len(lat), 2),
            "min_ms": round(min(lat), 2),
        }
    print(f"[verify] torch_cpu: {report['latency']['torch_cpu']}")

    report_path = out_dir / "export_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[export] report -> {report_path}")


if __name__ == "__main__":
    main()
