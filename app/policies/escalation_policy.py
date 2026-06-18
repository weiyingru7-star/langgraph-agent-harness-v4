"""
escalation_policy.py — 转人工规则

业务规则（来自 CLAUDE.md）:
    满足以下任一条件转人工:
        - emotion_score > 0.85
        - 用户明确要求人工
        - intent = complaint
        - errors 不为空

重要:
    不要让 LLM 直接决定是否转人工。
"""


def should_escalate(
    emotion_score: float,
    user_requested_human: bool,
    intent: str,
    errors: list,
) -> bool:
    """
    判断是否需要转人工。

    Args:
        emotion_score: 情绪评分 (0.0~1.0)
        user_requested_human: 用户是否明确要求人工
        intent: 用户意图
        errors: 错误列表

    Returns:
        True 表示需要转人工，False 表示继续自动处理
    """
    # TODO: 后续阶段实现完整转人工判断逻辑
    if emotion_score > 0.85:
        return True
    if user_requested_human:
        return True
    if intent == "complaint":
        return True
    if errors:
        return True
    return False
