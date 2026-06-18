"""
escalation_policy.py — 转人工规则

业务规则（来自 CLAUDE.md）：
    满足以下任一条件转人工：
        - emotion_score > 0.85
        - 用户明确要求人工
        - intent = complaint
        - errors 不为空

重要：
    不要让 LLM 直接决定是否转人工。
"""

from app.state.customer_state import CustomerServiceState


def decide_escalation(state: CustomerServiceState) -> dict:
    """
    判断是否需要转人工。

    读取字段: emotion_score, intent, errors
    写入字段: need_human, human_reason

    Args:
        state: 当前状态

    Returns:
        dict: {"need_human": bool, "human_reason": str | None}
    """
    reasons = []

    if state["emotion_score"] > 0.85:
        reasons.append("用户情绪评分过高")

    if state["intent"] == "human_request":
        reasons.append("用户要求转人工")

    if state["intent"] == "complaint":
        reasons.append("投诉需要人工处理")

    if state["errors"]:
        reasons.append(f"系统错误：{state['errors']}")

    if reasons:
        return {"need_human": True, "human_reason": "；".join(reasons)}
    return {"need_human": False, "human_reason": None}
