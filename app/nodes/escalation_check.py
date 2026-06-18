"""
escalation_check.py — 转人工检查节点

职责: 根据转人工规则判断是否需要将当前会话转接给人工客服。
"""

from app.state.customer_state import CustomerServiceState


def escalation_check(state: CustomerServiceState) -> CustomerServiceState:
    """
    检查是否需要转人工。

    转人工条件（在 escalation_policy.py 中定义）:
        - emotion_score > 0.85
        - 用户明确要求人工
        - intent = complaint
        - errors 不为空

    Args:
        state: 当前状态

    Returns:
        更新后的状态（包含 need_escalation 字段）
    """
    state.stage = "escalation_check"

    # TODO: 后续阶段调用 escalation_policy 进行判断
    state.need_escalation = False
    state.logs.append({
        "node": "escalation_check",
        "action": "转人工检查",
        "need_escalation": state.need_escalation,
    })

    return state
