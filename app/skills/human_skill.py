"""
human_skill.py — 转人工技能

职责: 将当前会话转接给人工客服处理。
"""

from app.state.customer_state import CustomerServiceState


def execute(state: CustomerServiceState) -> CustomerServiceState:
    """
    执行转人工技能。

    Args:
        state: 当前状态

    Returns:
        更新后的状态（包含 skill_result）
    """
    # TODO: 后续阶段实现转人工逻辑
    state.skill_result = {
        "skill": "human",
        "status": "pending",
    }

    return state
