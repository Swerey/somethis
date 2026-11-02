# -*- coding: utf-8 -*-
"""S3-A：多分类器对比评估（六分类违规识别）

对比对象：
1. dict      词典规则（badword_variants.json 变体匹配，静态词典，不含广告引流类）
2. bert_gpu  BERT improved（FastAPI /predict，HTTP 批量）
3. onnx_int8 ONNX int8 量化模型（onnxruntime CPU 本地批量）

指标：每类 P/R/F1、宏平均 F1、准确率、吞吐延迟。
产出：recognizer/outputs/eval/compare_report.json + compare_report.md

用法：python recognizer/eval_compare.py
"""
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import numpy as np
from transformers import AutoTokenizer

from config import LABEL_MAP, MAX_LEN, MODEL_NAME, OUTPUT_DIR

TEST_SET = r"C:\Users\swerey.SWEREY\PycharmProjects\系统\datasets\processed_v2\test.jsonl"
DICT_PATH = os.path.join(BASE_DIR, "badword_variants.json")
EVAL_DIR = Path(OUTPUT_DIR) / "eval"
EVAL_DIR.mkdir(parents=True, exist_ok=True)

LABEL_NAMES = [LABEL_MAP[i] for i in range(6)]
LABEL2ID = {name: i for i, name in enumerate(LABEL_NAMES)}

_PUNCT_RE = re.compile(r"[\s\u3000!！？?。，,、；;：:\"'“”‘’（）()\[\]【】《》〈〉<>.·…*#%@&~`^\-_/\\|+]+", re.UNICODE)
_DIGIT_MAP = str.maketrans("0123456789", "oizeasgtbg")
# 词典类别 -> 标签 id（词典不含广告引流，命中类别映射；未命中判正常）
DICT_LABEL_ID = {name: LABEL2ID[name] for name in ("辱骂暴力", "歧视煽动", "色情低俗", "敏感言论")}
_DICT_PRIORITY = ["色情低俗", "敏感言论", "辱骂暴力", "歧视煽动"]


def load_test():
    rows = []
    with open(TEST_SET, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rows.append((obj["text"], int(obj["label"])))
    return rows


def load_dict_index():
    with open(DICT_PATH, "r", encoding="utf-8") as f:
        d = json.load(f)
    index = []
    for label, items in d.items():
        if label not in DICT_LABEL_ID:
            continue
        for item in items:
            word = item.get("word", "")
            if word:
                index.append((word.lower(), label))
            for v in item.get("variants", []):
                v = str(v).strip()
                if v:
                    index.append((v.lower(), label))
    return index


def dict_predict(text: str, index) -> int:
    """词典分类器：归一化变体（小写/去标点/数字转字母）匹配；未命中判正常"""
    t = text.lower()
    variants = [t]
    t2 = _PUNCT_RE.sub("", t)
    if t2 and t2 != t:
        variants.append(t2)
    t3 = t2.translate(_DIGIT_MAP)
    if t3 and t3 != t2:
        variants.append(t3)
    hit = None
    for v in variants:
        for word, label in index:
            if word in v:
                pid = _DICT_PRIORITY.index(label) if label in _DICT_PRIORITY else 99
                if hit is None or pid < hit[0]:
                    hit = (pid, label)
    return DICT_LABEL_ID[hit[1]] if hit else 0


def predict_onnx(texts: list, sess, tokenizer, batch=128):
    preds = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        enc = tokenizer(chunk, truncation=True, padding=True, max_length=MAX_LEN,
                        return_tensors="np")
        logits = sess.run(["logits"], {
            "input_ids": enc["input_ids"].astype(np.int64),
            "attention_mask": enc["attention_mask"].astype(np.int64),
        })[0]
        preds.extend(logits.argmax(axis=-1).tolist())
    return preds


def predict_http(texts: list, port=8000, batch=64):
    import urllib.request
    preds = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/predict",
            data=json.dumps({"texts": chunk}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
        preds.extend(res["label_id"] for res in data["results"])
    return preds


def metrics(gt, pred, nclass=6):
    acc = sum(1 for a, b in zip(gt, pred) if a == b) / len(gt)
    rows = {}
    for c in range(nclass):
        tp = sum(1 for a, b in zip(gt, pred) if a == c and b == c)
        fp = sum(1 for a, b in zip(gt, pred) if a != c and b == c)
        fn = sum(1 for a, b in zip(gt, pred) if a == c and b != c)
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        rows[LABEL_NAMES[c]] = {"p": round(p, 4), "r": round(r, 4), "f1": round(f1, 4)}
    macro_f1 = sum(rows[n]["f1"] for n in LABEL_NAMES) / nclass
    return acc, rows, macro_f1


def main():
    print("[eval] 加载测试集")
    t0 = time.perf_counter()
    rows = load_test()
    print(f"[eval] test={len(rows)} 用时={time.perf_counter()-t0:.1f}s")

    # 类别分布
    dist = defaultdict(int)
    for _, lb in rows:
        dist[LABEL_NAMES[lb]] += 1
    print("[eval] 分布:", dict(dist))

    texts = [t for t, _ in rows]
    gts = [g for _, g in rows]

    # 1) 词典
    print("[eval] 词典规则预测中")
    index = load_dict_index()
    t0 = time.perf_counter()
    dict_pred = [dict_predict(t, index) for t in texts]
    dict_time = time.perf_counter() - t0
    acc_dict, mdict, macro1 = metrics(gts, dict_pred)
    print(f"[eval] dict: acc={acc_dict:.4f} macro_f1={macro1:.4f} 用时={dict_time:.2f}s")

    # 2) BERT GPU (HTTP)
    print("[eval] BERT GPU 预测中")
    t0 = time.perf_counter()
    bert_pred = predict_http(texts)
    bert_time = time.perf_counter() - t0
    acc_bert, mbert, macro2 = metrics(gts, bert_pred)
    print(f"[eval] bert_gpu: acc={acc_bert:.4f} macro_f1={macro2:.4f} 用时={bert_time:.1f}s")

    # 3) ONNX int8 CPU
    print("[eval] ONNX int8 预测中")
    import onnxruntime as ort
    int8_path = Path(OUTPUT_DIR) / "onnx" / "model_int8.onnx"
    sess = ort.InferenceSession(str(int8_path), providers=["CPUExecutionProvider"])
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, local_files_only=True)
    t0 = time.perf_counter()
    onnx_pred = predict_onnx(texts, sess, tokenizer)
    onnx_time = time.perf_counter() - t0
    acc_onnx, monnx, macro3 = metrics(gts, onnx_pred)
    print(f"[eval] onnx_int8: acc={acc_onnx:.4f} macro_f1={macro3:.4f} 用时={onnx_time:.1f}s")

    # 一致性：BERT vs ONNX
    agree = sum(1 for a, b in zip(bert_pred, onnx_pred) if a == b) / len(bert_pred)

    report = {
        "test_set": str(TEST_SET),
        "n_samples": len(rows),
        "distribution": dict(dist),
        "models": {
            "dict_rules": {"acc": round(acc_dict, 4), "macro_f1": round(macro1, 4),
                           "time_s": round(dict_time, 2), "per_class": mdict},
            "bert_gpu": {"acc": round(acc_bert, 4), "macro_f1": round(macro2, 4),
                         "time_s": round(bert_time, 1), "per_class": mbert},
            "onnx_int8": {"acc": round(acc_onnx, 4), "macro_f1": round(macro3, 4),
                          "time_s": round(onnx_time, 1), "per_class": monnx},
        },
        "bert_onnx_agreement": round(agree, 4),
    }

    out_json = EVAL_DIR / "compare_report.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown 报告
    md = ["# 多分类器对比评估报告（S3-A）", "",
          f"- 测试集：`{TEST_SET}`（{len(rows)} 条，六分类）",
          f"- 词典类别分布：{json.dumps(dict(dist), ensure_ascii=False)}",
          f"- BERT 与 ONNX int8 预测一致率：{agree:.4f}", "",
          "## 总体指标", "",
          "| 模型 | 准确率 | 宏平均F1 | 推理耗时 |",
          "|------|--------|---------|---------|",
          f"| 词典规则 | {report['models']['dict_rules']['acc']:.4f} | {report['models']['dict_rules']['macro_f1']:.4f} | {report['models']['dict_rules']['time_s']:.1f}s |",
          f"| BERT GPU | {report['models']['bert_gpu']['acc']:.4f} | {report['models']['bert_gpu']['macro_f1']:.4f} | {report['models']['bert_gpu']['time_s']:.1f}s |",
          f"| ONNX int8 CPU | {report['models']['onnx_int8']['acc']:.4f} | {report['models']['onnx_int8']['macro_f1']:.4f} | {report['models']['onnx_int8']['time_s']:.1f}s |",
          "", "## 每类 F1 对比", "",
          "| 类别 | 词典 | BERT GPU | ONNX int8 |",
          "|------|------|----------|-----------|"]
    for name in LABEL_NAMES:
        md.append(f"| {name} | {mdict[name]['f1']:.4f} | {mbert[name]['f1']:.4f} | {monnx[name]['f1']:.4f} |")
    md += ["", "## 说明", "",
           "- 词典规则仅覆盖 4 类违规词（辱骂暴力/歧视煽动/色情低俗/敏感言论），广告引流类全判正常，故 F1 为 0。",
           "- BERT GPU 与 ONNX int8 为同一模型的两种部署后端，指标应基本一致，差异源于 int8 量化精度损失。",
           "- 推理耗时为全量 5331 条处理时长：BERT GPU 走 HTTP 批量（含序列化）；ONNX int8 为本地 CPU 批量。"]
    out_md = EVAL_DIR / "compare_report.md"
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"[eval] 报告已写入 {out_json} / {out_md}")


if __name__ == "__main__":
    main()
