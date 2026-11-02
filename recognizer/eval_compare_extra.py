# -*- coding: utf-8 -*-
"""S3-B：补齐 BERT 基线 / TextCNN / BiLSTM 在同一测试集上的对比评估

复用 eval_compare 的加载与指标逻辑，产出：
- recognizer/outputs/eval/extra_report.json
- recognizer/outputs/eval/compare_report_full.md（合并 S3-A 与 S3-B）

用法：python recognizer/eval_compare_extra.py
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
sys.path.insert(0, r"C:\Users\swerey.SWEREY\PycharmProjects\PythonProject2\training")

import jieba
import torch
import torch.nn as nn
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from config import LABEL_MAP, MAX_LEN, MODEL_NAME
from train_textcnn import TextCNN
from train_bilstm import BiLSTMAttn

TEST_SET = r"C:\Users\swerey.SWEREY\PycharmProjects\系统\datasets\processed_v2\test.jsonl"
TRAIN_SET = r"C:\Users\swerey.SWEREY\PycharmProjects\系统\datasets\processed_v2\train.jsonl"
# 显式使用 recognizer 产物目录（避免与旧项目 training/config 的 OUTPUT_DIR 冲突）
EVAL_DIR = Path(r"C:\Users\swerey.SWEREY\PycharmProjects\系统\recognizer\outputs\eval")
CNN_OUT = Path(r"C:\Users\swerey.SWEREY\PycharmProjects\系统\recognizer\outputs")

LABEL_NAMES = [LABEL_MAP[i] for i in range(6)]


def load_rows(path):
    texts, labels = [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            texts.append(o["text"])
            labels.append(int(o["label"]))
    return texts, labels


def build_vocab(texts, vocab_size=20000):
    """与训练时 dataset_loader.build_vocab 完全一致（仅按词频降序，保持同频插入序）"""
    word_freq = {}
    for text in texts:
        for w in jieba.lcut(text):
            word_freq[w] = word_freq.get(w, 0) + 1
    sorted_words = sorted(word_freq.items(), key=lambda x: -x[1])
    vocab = {"[PAD]": 0, "[UNK]": 1}
    for w, _ in sorted_words[: vocab_size - 2]:
        vocab[w] = len(vocab)
    return vocab


def tokenize_and_pad(texts, vocab, max_len=128):
    ids = []
    for text in texts:
        toks = jieba.lcut(text)
        t = [vocab.get(w, 1) for w in toks][:max_len]
        ids.append(t + [0] * (max_len - len(t)))
    return torch.tensor(ids, dtype=torch.long)


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
    return acc, rows, sum(rows[n]["f1"] for n in LABEL_NAMES) / nclass


def best_ckpt(model_dir):
    best, best_m = None, -1.0
    for c in sorted(Path(model_dir).glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1])):
        st = json.loads((c / "trainer_state.json").read_text(encoding="utf-8"))
        if st.get("best_metric", -1.0) > best_m:
            best_m = st["best_metric"]
            best = str(c)
    return best


def main():
    print("[extra] 加载测试集")
    texts, gts = load_rows(TEST_SET)
    print(f"[extra] test={len(texts)}")

    # 1) BERT baseline（本地最优 checkpoint）
    print("[extra] BERT baseline 预测中")
    ckpt = best_ckpt(CNN_OUT / "bert_baseline")
    print(f"[extra] baseline ckpt = {ckpt}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(ckpt, local_files_only=True)
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    t0 = time.perf_counter()
    baseline_pred = []
    with torch.no_grad():
        for i in range(0, len(texts), 64):
            enc = tokenizer(texts[i:i + 64], truncation=True, padding=True,
                            max_length=MAX_LEN, return_tensors="pt").to(device)
            logits = model(**enc).logits
            baseline_pred.extend(logits.argmax(dim=1).tolist())
    baseline_time = time.perf_counter() - t0
    acc_b, m_b, macro_b = metrics(gts, baseline_pred)
    print(f"[extra] bert_baseline: acc={acc_b:.4f} macro_f1={macro_b:.4f} 用时={baseline_time:.1f}s")

    # 2) TextCNN / BiLSTM：重建训练同源 vocab（基于 processed_v2/train.jsonl）
    print("[extra] 构建 CNN 词表（jieba，基于 train.jsonl）")
    train_texts, _ = load_rows(TRAIN_SET)
    vocab = build_vocab(train_texts)
    input_ids = tokenize_and_pad(texts, vocab)

    results = {}
    for name, cls in (("textcnn", TextCNN), ("bilstm", BiLSTMAttn)):
        print(f"[extra] {name} 预测中")
        m = cls()
        sd = torch.load(CNN_OUT / name / "best_model.pt", map_location="cpu")
        m.load_state_dict(sd)
        m.eval()
        m.to(device)
        preds = []
        t0 = time.perf_counter()
        with torch.no_grad():
            for i in range(0, len(texts), 256):
                batch = input_ids[i:i + 256].to(device)
                logits = m(batch)
                preds.extend(logits.argmax(dim=1).tolist())
        elapse = time.perf_counter() - t0
        acc, mrows, macro = metrics(gts, preds)
        print(f"[extra] {name}: acc={acc:.4f} macro_f1={macro:.4f} 用时={elapse:.1f}s")
        results[name] = {"acc": round(acc, 4), "macro_f1": round(macro, 4),
                         "time_s": round(elapse, 1), "per_class": mrows}

    report = {
        "test_set": str(TEST_SET),
        "n_samples": len(texts),
        "bert_baseline": {"acc": round(acc_b, 4), "macro_f1": round(macro_b, 4),
                          "time_s": round(baseline_time, 1), "per_class": m_b},
        "textcnn": results["textcnn"],
        "bilstm": results["bilstm"],
    }
    out = EVAL_DIR / "extra_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # 合并生成完整报告 md
    base = json.loads((EVAL_DIR / "compare_report.json").read_text(encoding="utf-8"))
    full = {
        "test_set": base["test_set"], "n_samples": base["n_samples"],
        "distribution": base["distribution"],
        "models": {**base["models"],
                   "bert_baseline": report["bert_baseline"],
                   "textcnn": report["textcnn"], "bilstm": report["bilstm"]},
        "bert_onnx_agreement": base["bert_onnx_agreement"],
    }
    (EVAL_DIR / "compare_report_full.json").write_text(
        json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# 多模型对比评估报告（S3，完整）", "",
          f"- 测试集：`{TEST_SET}`（{len(texts)} 条，六分类）",
          f"- 分布：{json.dumps(base['distribution'], ensure_ascii=False)}",
          f"- BERT 与 ONNX int8 预测一致率：{base['bert_onnx_agreement']:.4f}", "",
          "## 总体指标", "",
          "| 模型 | 准确率 | 宏平均F1 | 推理耗时(全量) |",
          "|------|--------|---------|---------|"]
    rows = [("词典规则", full["models"]["dict_rules"]),
            ("BERT 基线", full["models"]["bert_baseline"]),
            ("BERT 改进版(GPU)", full["models"]["bert_gpu"]),
            ("ONNX int8(CPU)", full["models"]["onnx_int8"]),
            ("TextCNN", full["models"]["textcnn"]),
            ("BiLSTM+Attention", full["models"]["bilstm"])]
    for name, d in rows:
        md.append(f"| {name} | {d['acc']:.4f} | {d['macro_f1']:.4f} | {d['time_s']:.1f}s |")
    md += ["", "## 每类 F1 对比", "",
           "| 类别 | 词典 | BERT基线 | BERT改进 | ONNX int8 | TextCNN | BiLSTM |",
           "|------|------|---------|---------|-----------|---------|--------|"]
    for name in LABEL_NAMES:
        md.append(f"| {name} | {full['models']['dict_rules']['per_class'][name]['f1']:.4f} "
                  f"| {full['models']['bert_baseline']['per_class'][name]['f1']:.4f} "
                  f"| {full['models']['bert_gpu']['per_class'][name]['f1']:.4f} "
                  f"| {full['models']['onnx_int8']['per_class'][name]['f1']:.4f} "
                  f"| {full['models']['textcnn']['per_class'][name]['f1']:.4f} "
                  f"| {full['models']['bilstm']['per_class'][name]['f1']:.4f} |")
    md += ["", "## 说明", "",
           "- 词典规则仅覆盖 4 类违规词（辱骂暴力/歧视煽动/色情低俗/敏感言论），广告引流类全判正常，故 F1 为 0。",
           "- BERT 基线与改进版、TextCNN/BiLSTM 均在同一测试集（processed_v2/test.jsonl）评估；",
           "  CNN 词表基于同源 processed_v2/train.jsonl 用 jieba 重建，与训练时一致。",
           "- 推理耗时为全量 5331 条处理时长；BERT 系列 GPU 推理，ONNX int8 为本地 CPU。",
           "- 改进版相对基线提升主要来自 FocalLoss（缓解类别不平衡）与 FGM（对抗训练）。"]
    (EVAL_DIR / "compare_report_full.md").write_text("\n".join(md), encoding="utf-8")
    print(f"[extra] 完整报告已写入 {EVAL_DIR / 'compare_report_full.md'}")


if __name__ == "__main__":
    main()
