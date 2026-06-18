"""
recommendation_skill.py — 商品推荐技能

职责: 根据用户需求和偏好推荐合适的商品。
"""

from app.state.customer_state import CustomerServiceState


def execute(state: CustomerServiceState) -> CustomerServiceState:
    """
    执行商品推荐技能。

    Args:
        state: 当前状态

    Returns:
        更新后的状态（包含 skill_result）
    """
    # TODO: 后续阶段实现推荐逻辑
    state.skill_result = {
        "skill": "recommendation",
        "status": "pending",
    }

    return state
