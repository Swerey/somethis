"""审核规则模块：违规词变体词典加载、文本归一化与快速命中判定"""
import json
import os
import re

from config import DICTIONARY_PATH

# M6：词典路径集中到 config（默认指向 PythonProject2/training/badword_variants.json，可用 BADWORD_DICT 覆盖）
DEFAULT_DICT = DICTIONARY_PATH

# 类别 -> 风险等级（词典命中直接定级，不再调模型）
LABEL_RISK = {
    "色情低俗": "high",
    "敏感言论": "high",
    "涉政": "high",
    "辱骂暴力": "mid",
    "暴力威胁": "mid",
    "歧视煽动": "mid",
    "广告引流": "low",
}

_loaded = False
_dictionary = {}   # {"类别": [{"word": ..., "variants": [...]}]}
_index = []        # [(word_lower, label, risk)]  用于快速匹配

# 标点 / 空白（含全角空格）——用于变体归一化去除
_PUNCT_RE = re.compile(r"[\s\u3000!！？?。，,、；;：:\"'“”‘’（）()\[\]【】《》〈〉<>.·…*#%@&~`^\-_/\\|+]+", re.UNICODE)
# 数字 -> 近似字母（用于识别"数字替换"变体，如 0->o / 8->b / 3->e）
_DIGIT_MAP = str.maketrans("0123456789", "oizeasgtbg")


def normalize_variants(text: str) -> list:
    """生成文本的归一化变体列表（T13：谐音/拼音/数字替换/去标点空格）。

    返回顺序：小写原文 -> 去标点去空格 -> 去标点去空格+数字转字母。
    后续层级越激进，用于对抗变体；命中词典词即视为命中。
    """
    t = text.lower()
    variants = [t]
    t2 = _PUNCT_RE.sub("", t)
    if t2 and t2 != t:
        variants.append(t2)
    t3 = t2.translate(_DIGIT_MAP)
    if t3 and t3 != t2:
        variants.append(t3)
    seen, out = set(), []
    for v in variants:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def load_dictionary(path: str = None) -> dict:
    """加载违规词变体词典，返回原始 dict；随后合并管理端 banned_words 表词条"""
    global _loaded, _dictionary, _index
    path = path or DEFAULT_DICT
    with open(path, "r", encoding="utf-8") as f:
        _dictionary = json.load(f)
    _index = []
    for label, items in _dictionary.items():
        risk = LABEL_RISK.get(label, "mid")
        for item in items:
            word = item.get("word", "")
            if word:
                _index.append((word.lower(), label, risk))
            for v in item.get("variants", []):
                v = str(v).strip()
                if v:
                    _index.append((v.lower(), label, risk))
    _merge_db_words()
    _loaded = True
    return _dictionary


def _merge_db_words():
    """把管理端维护的 banned_words 表（enabled=1）合入索引（表不存在时跳过）"""
    try:
        from db import db_cursor
        with db_cursor() as cur:
            rows = cur.execute(
                "SELECT word, category, risk_level FROM banned_words WHERE enabled=1"
            ).fetchall()
        existing = {w for w, _, _ in _index}
        for r in rows:
            word = (r["word"] or "").strip().lower()
            if not word or word in existing:
                continue
            risk = r["risk_level"] or LABEL_RISK.get(r["category"], "mid")
            _index.append((word, r["category"] or "辱骂暴力", risk))
            existing.add(word)
    except Exception:
        pass  # 表不存在 / 数据库未初始化：仅使用静态词典


def reload_dictionary(path: str = None) -> dict:
    """重新加载词典（管理端增删违规词后调用，使新词立即生效）"""
    global _loaded
    _loaded = False
    return load_dictionary(path)


def quick_check(text: str):
    """词典快速判定：命中返回 (label, risk, matched_words)，未命中返回 None。

    优先级：高危类别优先（敏感言论/色情低俗）> 中危类别（辱骂暴力/歧视煽动）。
    对文本的多个归一化变体（谐音/拼音/数字替换/去标点空格）均执行匹配。
    """
    if not _loaded:
        load_dictionary()
    if not text:
        return None
    matched = []
    for variant in normalize_variants(text):
        for word, label, risk in _index:
            if word in variant:
                matched.append({"word": word, "label": label, "risk": risk})
    if not matched:
        return None
    # 取最高风险
    priority = {"high": 0, "mid": 1, "low": 2}
    best = min(matched, key=lambda m: priority[m["risk"]])
    words = [m["word"] for m in matched if m["label"] == best["label"]]
    return best["label"], best["risk"], words


# ---- S5 本地规则降级：识别服务不可用时的兜底审核（本地规则先审）----
# 常见高危/中危/低危特征正则（与词典互补，覆盖词典未收录的常见变体表达）
_LOCAL_PATTERNS = [
    # (风险等级, 正则, 类别标签)
    ("high", re.compile(r"(习近平|习大大|共[产産]党|[政教]治敏感|颠覆|分裂|台独|藏独|疆独|法轮|邪教|反[动对]|暴[乱力]|枪|毒[品枭]|制毒|卖淫|嫖|约炮|裸[聊照]|色情|淫秽|下流|黄[色片]|AV|成人网站)", re.I), "敏感言论"),
    ("high", re.compile(r"(习总|维[稳]|六四|天安门事件|敏感时期)", re.I), "敏感言论"),
    ("mid", re.compile(r"(傻逼|煞笔|沙比|妈的|草泥马|去死|废物|垃圾|滚蛋|操你|我操|fuck|cnm|nmsl|wcnm|tmd|md|狗东西|贱人|白痴|脑残)", re.I), "辱骂暴力"),
    ("mid", re.compile(r"(黑鬼|白皮猪|支那|东亚病夫|肥猪|丑八怪|歧视|地域黑|河南人|东北人|黑人|穆斯林|同性恋|娘炮|直男癌|女拳)", re.I), "歧视煽动"),
    ("low", re.compile(r"(加微信|加V|加v|扫码|二维码|私聊|代刷|刷单|兼职|日赚|月入|稳赚|代理|微商|广告|推广|返利|抽奖|领奖|秒到|彩票|博彩|赌博)", re.I), "广告引流"),
]


def local_fallback_check(text: str):
    """本地规则降级审核：识别服务不可用时的兜底判定。

    命中返回 (label, risk, matched_words)；未命中返回 None（调用方按低危放行处理）。
    先走词典变体快判（覆盖谐音/拼音/数字替换），再走特征正则兜底。
    """
    hit = quick_check(text)
    if hit is not None:
        return hit
    matched = []
    for risk, pattern, label in _LOCAL_PATTERNS:
        if pattern.search(text or ""):
            matched.append({"word": pattern.pattern[:12], "label": label, "risk": risk})
    if not matched:
        return None
    priority = {"high": 0, "mid": 1, "low": 2}
    best = min(matched, key=lambda m: priority[m["risk"]])
    words = [m["word"] for m in matched if m["label"] == best["label"]]
    return best["label"], best["risk"], words
