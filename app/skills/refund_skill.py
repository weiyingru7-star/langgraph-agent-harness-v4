"""
refund_skill.py — 退款处理技能

职责: 执行退款流程，包括查询退款政策、计算退款金额等。
"""

from app.state.customer_state import CustomerServiceState


def execute(state: CustomerServiceState) -> CustomerServiceState:
    """
    执行退款处理技能。

    Args:
        state: 当前状态

    Returns:
        更新后的状态（包含 skill_result）
    """
    # TODO: 后续阶段实现退款处理逻辑
    state.skill_result = {
        "skill": "refund",
        "status": "pending",
    }

    return state
