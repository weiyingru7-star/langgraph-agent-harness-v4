"""
logistics_skill.py — 物流查询技能

职责: 查询订单物流信息，包括配送状态、预计到达时间等。
"""

from app.state.customer_state import CustomerServiceState


def execute(state: CustomerServiceState) -> CustomerServiceState:
    """
    执行物流查询技能。

    Args:
        state: 当前状态

    Returns:
        更新后的状态（包含 skill_result）
    """
    # TODO: 后续阶段实现物流查询逻辑
    state.skill_result = {
        "skill": "logistics",
        "status": "pending",
    }

    return state
