"""
safety.py — LLM 输出安全检查。

检查 LLM 回复是否包含危险承诺，确保不绕过 Policy。
"""

from typing import Any, Dict, List

# 绝对不允许出现的危险词
_DANGEROUS_TERMS: List[str] = [
    "已经退款",
    "已退款成功",
    "退款已完成",
    "已经帮您退款",
    "我已经帮您退款",
    "已补发",
    "已赔偿",
    "已取消订单",
    "已修改地址",
    "已为您处理完成",
    "已经发货",
    "已经帮您处理",
    "补偿您",
]

# need_human=True 时，回复中必须包含的人工相关词
_HUMAN_KEYWORDS = ["人工", "客服", "专员"]


def validate_llm_reply(reply: str, state: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    检查 LLM 回复是否安全。

    Args:
        reply: LLM 生成的回复文本
        state: 当前 state（可选），用于检查 need_human 等

    Returns:
        {"safe": bool, "reason": str, "blocked_terms": list}
    """
    blocked: List[str] = []

    for term in _DANGEROUS_TERMS:
        if term in reply:
            blocked.append(term)

    if blocked:
        return {"safe": False, "reason": f"回复包含危险承诺: {'; '.join(blocked)}", "blocked_terms": blocked}

    # 如果 need_human=True，回复中必须包含人工相关词
    if state and state.get("need_human"):
        if not any(kw in reply for kw in _HUMAN_KEYWORDS):
            return {
                "safe": False,
                "reason": "need_human=True 但回复未提及人工/客服/专员",
                "blocked_terms": [],
            }

    return {"safe": True, "reason": "", "blocked_terms": []}
