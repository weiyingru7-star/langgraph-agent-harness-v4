"""
product_qa_skill.py — 商品咨询技能

职责: 回答用户关于商品的各类问题，如规格、材质、价格等。
"""

from app.state.customer_state import CustomerServiceState


def execute(state: CustomerServiceState) -> CustomerServiceState:
    """
    执行商品问答技能。

    Args:
        state: 当前状态

    Returns:
        更新后的状态（包含 skill_result）
    """
    # TODO: 后续阶段实现商品问答逻辑
    state.skill_result = {
        "skill": "product_qa",
        "status": "pending",
    }

    return state
