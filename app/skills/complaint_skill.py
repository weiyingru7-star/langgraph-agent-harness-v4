"""
complaint_skill.py — 投诉处理技能

职责: 处理用户投诉，记录投诉内容并进行安抚。
"""

from app.state.customer_state import CustomerServiceState


def execute(state: CustomerServiceState) -> CustomerServiceState:
    """
    执行投诉处理技能。

    Args:
        state: 当前状态

    Returns:
        更新后的状态（包含 skill_result）
    """
    # TODO: 后续阶段实现投诉处理逻辑
    state.skill_result = {
        "skill": "complaint",
        "status": "pending",
    }

    return state
