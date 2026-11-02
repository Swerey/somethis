"""违规词变体数据增强 — 针对辱骂暴力/歧视煽动等弱类
读取 train.jsonl -> 命中变体词典的样本生成变体样本 + 弱类上采样 -> train_aug.jsonl
"""
import json
import os
import random

random.seed(42)

DATA_DIR = r"C:\Users\swerey.SWEREY\PycharmProjects\PythonProject2\data\processed_v2"
TRAIN = os.path.join(DATA_DIR, "train.jsonl")
AUG = os.path.join(DATA_DIR, "train_aug.jsonl")
DICT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "badword_variants.json")

LABEL_TO_CNAME = {0: "正常", 1: "色情低俗", 2: "辱骂暴力", 3: "广告引流", 4: "敏感言论", 5: "歧视煽动"}
CNAME_TO_LABEL = {v: k for k, v in LABEL_TO_CNAME.items()}

# 目标样本数（弱类上采样）
TARGET = {"辱骂暴力": 6000, "歧视煽动": 6000}


def load_jsonl(path):
    objs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            objs.append(json.loads(line))
    return objs


def save_jsonl(path, objs):
    with open(path, "w", encoding="utf-8") as f:
        for o in objs:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")


def load_dict():
    with open(DICT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def gen_variant(text, entries, rng):
    """对命中词做变体替换，返回替换后的文本；无命中返回 None"""
    # 按词长降序，避免子串冲突
    hits = []
    for e in entries:
        w = e["word"]
        if w in text:
            hits.append(e)
    if not hits:
        return None
    hits.sort(key=lambda e: len(e["word"]), reverse=True)
    # 随机替换 1~2 个命中词
    k = rng.randint(1, min(2, len(hits)))
    chosen = rng.sample(hits, k)
    new_text = text
    for e in chosen:
        var = rng.choice(e["variants"])
        new_text = new_text.replace(e["word"], var, 1)
    if new_text == text:
        return None
    return new_text


def main():
    objs = load_jsonl(TRAIN)
    rng = random.Random(42)
    dict_data = load_dict()
    # 类别 -> entries
    cat_entries = {cname: d["variants"] if False else d for cname, d in dict_data.items()}

    from collections import Counter
    stats = Counter(o["label"] for o in objs)

    out = list(objs)  # 原始样本保留
    added = Counter()

    for o in objs:
        label = o["label"]
        cname = LABEL_TO_CNAME[label]
        entries = dict_data.get(cname, [])
        if not entries:
            continue
        # 最多生成 2 条变体样本
        for _ in range(2):
            new_text = gen_variant(o["text"], entries, rng)
            if new_text is None:
                break
            out.append({"text": new_text, "label": label})
            added[label] += 1

    # 弱类上采样补足目标
    for cname, target in TARGET.items():
        label = CNAME_TO_LABEL[cname]
        cur = stats[label] + added[label]
        if cur >= target:
            continue
        # 收集该类原始样本
        pool = [o for o in objs if o["label"] == label]
        entries = dict_data.get(cname, [])
        need = target - cur
        for _ in range(need):
            o = rng.choice(pool)
            new_text = gen_variant(o["text"], entries, rng) or o["text"]
            out.append({"text": new_text, "label": label})
            added[label] += 1

    save_jsonl(AUG, out)
    final = Counter(o["label"] for o in out)
    print("=== 增强结果 ===")
    print("原训练集:", dict(stats), "总", len(objs))
    print("新增变体样本:", dict(added), "总", sum(added.values()))
    print("增强后:", {LABEL_TO_CNAME[k]: v for k, v in sorted(final.items())}, "总", len(out))


if __name__ == "__main__":
    main()
