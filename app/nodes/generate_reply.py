"""
generate_reply.py — 回复生成节点

职责: 根据技能执行结果和当前状态生成最终回复文本。
"""

from app.state.customer_state import CustomerServiceState


def generate_reply(state: CustomerServiceState) -> CustomerServiceState:
    """
    生成给用户的回复文本。

    Args:
        state: 当前状态

    Returns:
        更新后的状态（包含 reply 字段）
    """
    state.stage = "generate_reply"

    # TODO: 后续阶段实现回复生成
    state.reply = ""
    state.logs.append({
        "node": "generate_reply",
        "action": "生成回复",
        "reply_length": len(state.reply),
    })

    return state
