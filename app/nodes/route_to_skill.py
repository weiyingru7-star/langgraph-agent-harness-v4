"""
route_to_skill.py — 路由节点

职责: 根据意图分析结果将流程路由到对应的技能处理节点。
"""

from app.state.customer_state import CustomerServiceState


def route_to_skill(state: CustomerServiceState) -> CustomerServiceState:
    """
    根据 intent 路由到对应技能。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    state.stage = "route"

    # TODO: 后续阶段实现完整路由逻辑
    state.logs.append({
        "node": "route_to_skill",
        "action": "路由到技能",
        "intent": state.intent,
        "routed_to": "",
    })

    return state
