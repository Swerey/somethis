"""审核管线：词典命中即分级处置，未命中调模型；存疑内容先放行并上报管理员"""
import logging
import time

from db import db_cursor
from models import (
    LABEL_MAP, LABEL_RISK, CREDIT_PENALTY, CREDIT_RECOVER, CREDIT_DAILY_RECOVER_LIMIT,
    STATUS_VISIBLE, STATUS_FOLDED, STATUS_BLOCKED, STATUS_WARNED,
    REVIEW_PENDING, REVIEW_AUTO_FOLDED,
)
from audit import rules, engine
from audit_logs import write_audit_log

logger = logging.getLogger("audit")

# T14：高危类别直接拦截所需置信度阈值（低于该值判存疑，放行后上报人工）
HIGH_RISK_CONFIDENCE = 0.85


def _source_table(source_type: str):
    """存疑/内容状态联动：source_type -> 内容表名"""
    return {
        "posts": "posts",
        "comments": "comments",
        "video_comment": "video_comments",
        "danmaku": "danmaku",
        "live": "live_messages",
    }.get(source_type)


def _write_credit_log(cur, user_id, delta, reason, ref_id=0):
    cur.execute(
        "INSERT INTO credit_log (user_id, delta, reason, ref_id) VALUES (?,?,?,?)",
        (user_id, delta, reason, ref_id),
    )


def _compute_weighted_penalty(cur, user_id, source_type, source_id, risk_level):
    """信用分权重细化（批次二）：基础扣分 + 历史违规次数 + 被举报次数 - 申诉通过率修正

    - 历史未回退违规每 5 次加扣 1 分（封顶 +2）
    - 本内容待处理举报每条加扣 1 分（封顶 +2）
    - 申诉通过率 >= 60% 视为误判风险高，减免 1 分（最低扣 1 分）
    返回 (penalty, detail)。
    """
    base = CREDIT_PENALTY.get(risk_level, 1)
    history = cur.execute(
        """SELECT COUNT(*) FROM violations
           WHERE user_id=? AND reverted=0""", (user_id,)
    ).fetchone()[0]
    report_cnt = cur.execute(
        """SELECT COUNT(*) FROM reports
           WHERE target_type=? AND target_id=? AND status='pending'""",
        (source_type, source_id),
    ).fetchone()[0]
    try:
        appeal_stat = cur.execute(
            """SELECT
                 SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS ok,
                 SUM(CASE WHEN status IN ('approved','rejected') THEN 1 ELSE 0 END) AS total
               FROM appeals WHERE user_id=?""", (user_id,)
        ).fetchone()
        rate = (appeal_stat["ok"] / appeal_stat["total"]) if appeal_stat and appeal_stat["total"] else 0.0
    except Exception:
        rate = 0.0
    penalty = base + min(2, history // 5) + min(2, report_cnt)
    if rate >= 0.6 and penalty > 1:
        penalty -= 1
    detail = f"base={base}"
    if history // 5:
        detail += f"+hist{min(2, history // 5)}"
    if report_cnt:
        detail += f"+rep{min(2, report_cnt)}"
    if rate >= 0.6:
        detail += f"-appeal({rate:.2f})"
    return penalty, detail


def _record_violation(user_id, content, source_type, source_id, label, risk_level, action,
                      _conn=None):
    """写入违规记录并扣除信用分（联动写信用流水 credit_log）

    批次二：扣分采用加权策略（基础 + 历史违规 + 被举报 - 申诉通过率修正）。
    _conn: 可选外层游标/连接。传入时复用外层连接（避免嵌套 db_cursor 造成自死锁）。
    """
    if _conn is not None:
        cur = _conn if hasattr(_conn, "execute") else _conn.cursor()
        penalty, wdetail = _compute_weighted_penalty(
            cur, user_id, source_type, source_id, risk_level)
        cur.execute(
            """INSERT INTO violations (user_id, content, source_type, source_id, label, risk_level, action)
               VALUES (?,?,?,?,?,?,?)""",
            (user_id, content, source_type, source_id, label, risk_level, action),
        )
        vid = cur.lastrowid
        cur.execute(
            "UPDATE users SET credit_score = MAX(0, credit_score - ?) WHERE id = ?",
            (penalty, user_id),
        )
        _write_credit_log(cur, user_id, -penalty, f"违规扣分（{label}/{risk_level}）[{wdetail}]", vid)
        return penalty
    with db_cursor() as cur:
        penalty, wdetail = _compute_weighted_penalty(
            cur, user_id, source_type, source_id, risk_level)
        cur.execute(
            """INSERT INTO violations (user_id, content, source_type, source_id, label, risk_level, action)
               VALUES (?,?,?,?,?,?,?)""",
            (user_id, content, source_type, source_id, label, risk_level, action),
        )
        vid = cur.lastrowid
        cur.execute(
            "UPDATE users SET credit_score = MAX(0, credit_score - ?) WHERE id = ?",
            (penalty, user_id),
        )
        _write_credit_log(cur, user_id, -penalty, f"违规扣分（{label}/{risk_level}）[{wdetail}]", vid)
    return penalty


def _recover_credit(user_id):
    """内容通过审核：恢复 1 分（上限 100；每日最多 CREDIT_DAILY_RECOVER_LIMIT 分，T12）"""
    with db_cursor() as cur:
        today = time.strftime("%Y-%m-%d 00:00:00")
        recovered = cur.execute(
            "SELECT COUNT(*) FROM credit_log WHERE user_id=? AND delta>0 AND created_at >= ?",
            (user_id, today),
        ).fetchone()[0]
        if recovered >= CREDIT_DAILY_RECOVER_LIMIT:
            return False
        cur.execute(
            "UPDATE users SET credit_score = MIN(100, credit_score + ?) WHERE id = ?",
            (CREDIT_RECOVER, user_id),
        )
        _write_credit_log(cur, user_id, CREDIT_RECOVER, "内容通过审核")
    return True


def enqueue_review(source_type: str, source_id: int, user_id: int, content: str,
                   label: str = "", risk_level: str = "mid") -> int:
    """写入存疑上报队列（review_queue），返回队列条目 id。

    由路由在内容成功入库、拿到内容 id 后调用（source_id 为对应内容 id）。
    M6：上报同时写审计日志（action=review_enqueue）。
    """
    with db_cursor() as cur:
        cur.execute(
            """INSERT INTO review_queue (source_type, source_id, user_id, content, label, risk_level)
               VALUES (?,?,?,?,?,?)""",
            (source_type, source_id, user_id, content, label, risk_level),
        )
        qid = cur.lastrowid
        write_audit_log(
            operator_id=user_id, action="review_enqueue",
            target_type=source_type, target_id=source_id,
            detail=f"存疑上报（{label or '未知'}/{risk_level}）queue_id={qid}", cur=cur,
        )
        logger.info("review_enqueue source_type=%s source_id=%s user_id=%s label=%s risk=%s queue_id=%s",
                    source_type, source_id, user_id, label, risk_level, qid)
        return qid


def _base_result():
    return {
        "status": STATUS_VISIBLE,
        "label": "正常",
        "risk_level": "low",
        "action": "放行",
        "matched_words": [],
        "model_hit": False,
        "model_latency": None,
        "confidence": None,
        "needs_review": False,
        "review_label": "",
        "review_risk": "",
        "message": "内容正常",
    }


def _apply_dict_hit(text, user_id, source_type, source_id, label, risk, words) -> dict:
    """词典命中分级处置（不调模型）。M6：拦截/折叠/提示均写审计日志与运行日志。"""
    result = _base_result()
    result.update(matched_words=words, label=label, risk_level=risk)
    if risk == "high":
        result.update(status=STATUS_BLOCKED, action="拦截",
                      message=f"命中违规词词典，已拦截（{label}）")
        _record_violation(user_id, text, source_type, source_id, label, risk, "blocked")
        write_audit_log(action="dict_block", target_type=source_type, target_id=source_id,
                        detail=f"词典命中拦截（{label}/{risk}）词条={words[:5]}")
        logger.info("dict_block source_type=%s source_id=%s user_id=%s label=%s words=%s",
                    source_type, source_id, user_id, label, words)
    elif risk == "mid":
        result.update(status=STATUS_FOLDED, action="折叠",
                      message=f"命中违规词词典，已折叠（{label}）")
        _record_violation(user_id, text, source_type, source_id, label, risk, "folded")
        write_audit_log(action="dict_fold", target_type=source_type, target_id=source_id,
                        detail=f"词典命中折叠（{label}/{risk}）词条={words[:5]}")
        logger.info("dict_fold source_type=%s source_id=%s user_id=%s label=%s words=%s",
                    source_type, source_id, user_id, label, words)
    else:
        result.update(status=STATUS_WARNED, action="提示",
                      message=f"命中违规词词典，低危提示（{label}）")
        _record_violation(user_id, text, source_type, source_id, label, risk, "warned")
        write_audit_log(action="dict_warn", target_type=source_type, target_id=source_id,
                        detail=f"词典命中提示（{label}/{risk}）词条={words[:5]}")
        logger.info("dict_warn source_type=%s source_id=%s user_id=%s label=%s words=%s",
                    source_type, source_id, user_id, label, words)
    return result


def _apply_model_item(text, user_id, source_type, source_id, item, latency_ms) -> dict:
    """模型单条结果处置（透传置信度并按置信度分级，T14）"""
    result = _base_result()
    label = item.get("label", "正常")
    result["model_hit"] = True
    result["model_latency"] = latency_ms
    probs = item.get("probabilities") or {}
    try:
        confidence = float(probs.get(label, 0.0) or 0.0)
    except Exception:
        confidence = 0.0
    result["confidence"] = round(confidence, 4)

    if label == "正常":
        result.update(message="模型判定正常")
        _recover_credit(user_id)
        return result

    risk = LABEL_RISK.get(label, "mid")
    if risk == "high" and confidence >= HIGH_RISK_CONFIDENCE:
        # 高危 + 高置信：直接拦截 + 记违规 + 审计日志
        result.update(status=STATUS_BLOCKED, label=label, risk_level=risk,
                      action="拦截", message=f"模型判定为{label}（置信度{confidence:.2f}），已拦截")
        _record_violation(user_id, text, source_type, source_id, label, risk, "blocked")
        write_audit_log(action="model_block", target_type=source_type, target_id=source_id,
                        detail=f"模型拦截（{label}/{risk}）置信度={confidence:.4f}")
        logger.info("model_block source_type=%s source_id=%s user_id=%s label=%s conf=%.4f",
                    source_type, source_id, user_id, label, confidence)
    else:
        # 中低危 或 高危低置信：先通过展示 + 上报管理端，待人工处理
        result.update(status=STATUS_VISIBLE, label=label, risk_level=risk,
                      action="放行（存疑上报）", needs_review=True,
                      review_label=label, review_risk=risk,
                      message=f"模型判定为{label}（置信度{confidence:.2f}），存疑放行，已上报管理员")
        logger.info("review_suspect source_type=%s source_id=%s user_id=%s label=%s conf=%.4f",
                    source_type, source_id, user_id, label, confidence)
    return result


def audit_text(text: str, user_id: int, source_type: str = "posts", source_id: int = 0) -> dict:
    """单条内容审核管线。

    返回 dict: {status, label, risk_level, action, matched_words, model_hit, model_latency,
                confidence, needs_review, review_label, review_risk, message}
    - status: visible / folded / blocked / warned
    - action: 放行 / 拦截 / 折叠 / 提示 / 放行（存疑上报）
    - needs_review: 模型判非正常但未达直接拦截条件，内容按 visible 放行并应上报管理端
    """
    text = (text or "").strip()
    if not text:
        return _base_result()

    # ---- 第一层：词典快判（命中即分级处置，不调模型）----
    hit = rules.quick_check(text)
    if hit is not None:
        label, risk, words = hit
        return _apply_dict_hit(text, user_id, source_type, source_id, label, risk, words)

    # ---- 第二层：模型判定 ----
    resp = engine.predict([text])
    if resp is None:
        # S5：识别服务不可用 → 本地规则先审（词典变体 + 特征正则），不再直接放行
        local_hit = rules.local_fallback_check(text)
        if local_hit is not None:
            label, risk, words = local_hit
            result = _apply_dict_hit(text, user_id, source_type, source_id, label, risk, words)
            result["message"] = f"识别服务暂不可用，本地规则命中（{label}）：{result['message']}"
            logger.warning("audit_service_offline fallback=local_rule hit=%s source_type=%s source_id=%s",
                           label, source_type, source_id)
            return result
        result = _base_result()
        result.update(message="识别服务暂不可用，本地规则未命中，已按放行处理")
        logger.warning("audit_service_offline source_type=%s source_id=%s user_id=%s, fallback pass",
                       source_type, source_id, user_id)
        _recover_credit(user_id)
        return result

    return _apply_model_item(text, user_id, source_type, source_id,
                             resp["results"][0], resp.get("latency_ms"))


def audit_batch(texts: list, user_id: int, source_type: str = "posts", source_id: int = 0) -> list:
    """批量审核（弹幕常用），返回与 texts 等长的结果列表。

    T02：词典快判逐条独立；未命中词典的文本合并为一次批量模型调用。
    """
    results = [None] * len(texts)
    dict_hits = {}   # idx -> (label, risk, words)
    unmatched = []   # [(idx, text)]

    for i, t in enumerate(texts):
        t = (t or "").strip()
        if not t:
            results[i] = _base_result()
            continue
        hit = rules.quick_check(t)
        if hit is not None:
            dict_hits[i] = hit
        else:
            unmatched.append((i, t))

    resp = None
    if unmatched:
        resp = engine.predict([t for _, t in unmatched])

    for i, t in enumerate(texts):
        if results[i] is not None:
            continue
        if i in dict_hits:
            label, risk, words = dict_hits[i]
            results[i] = _apply_dict_hit(t, user_id, source_type, source_id, label, risk, words)
            continue
        # 未命中词典：按模型结果处置；模型不可用时容错放行
        found = False
        if resp is not None:
            for k, (idx, _t) in enumerate(unmatched):
                if idx == i and k < len(resp["results"]):
                    results[i] = _apply_model_item(t, user_id, source_type, source_id,
                                                   resp["results"][k], resp.get("latency_ms"))
                    found = True
                    break
        if not found:
            # S5：模型批量调用不可用 → 本地规则先审（词典变体 + 特征正则），未命中才放行
            local_hit = rules.local_fallback_check(t)
            if local_hit is not None:
                label, risk, words = local_hit
                result = _apply_dict_hit(t, user_id, source_type, source_id, label, risk, words)
                result["message"] = f"识别服务暂不可用，本地规则命中（{label}）：{result['message']}"
                logger.warning("audit_service_offline fallback=local_rule hit=%s source_type=%s source_id=%s",
                               label, source_type, source_id)
                results[i] = result
                continue
            result = _base_result()
            result.update(message="识别服务暂不可用，本地规则未命中，已按放行处理")
            _recover_credit(user_id)
            results[i] = result
    return results


def audit_post(title: str, content: str, user_id: int, source_id: int = 0) -> dict:
    """帖子全文审核：标题 + 正文拼接后统一过管线"""
    text = f"{title}\n{content}"
    return audit_text(text, user_id, "posts", source_id)


def auto_fold_expired(hours: int = 24) -> int:
    """存疑队列超时自动折叠（T11）：超过 hours 未处理的 pending 条目置为 auto_folded，
    并把对应源内容状态改为 folded。返回折叠条数。M6：每条折叠写审计日志。"""
    with db_cursor() as cur:
        rows = cur.execute(
            """SELECT id, source_type, source_id FROM review_queue
               WHERE status=? AND created_at < datetime('now', 'localtime', ?)""",
            (REVIEW_PENDING, f"-{hours} hours"),
        ).fetchall()
        n = 0
        for r in rows:
            table = _source_table(r["source_type"])
            if table:
                cur.execute(f"UPDATE {table} SET status=? WHERE id=?",
                            (STATUS_FOLDED, r["source_id"]))
            cur.execute(
                """UPDATE review_queue SET status=?, handled_by=NULL,
                   handled_at=datetime('now','localtime') WHERE id=?""",
                (REVIEW_AUTO_FOLDED, r["id"]),
            )
            write_audit_log(action="review_auto_fold", target_type=r["source_type"],
                            target_id=r["source_id"], detail=f"存疑超时自动折叠 queue_id={r['id']}",
                            cur=cur)
            logger.info("review_auto_fold queue_id=%s source_type=%s source_id=%s",
                        r["id"], r["source_type"], r["source_id"])
            n += 1
    return n
