"""
analyze_multimodal.py — 多模态分析节点

职责: 当输入为 text_with_image 时，结合图片和文字进行综合分析。
"""

from app.state.customer_state import CustomerServiceState


def analyze_multimodal(state: CustomerServiceState) -> CustomerServiceState:
    """
    分析图文混合输入，提取意图和情绪。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    state.stage = "analyze_multimodal"

    state.logs.append({
        "node": "analyze_multimodal",
        "action": "分析多模态输入",
        "status": "pending",
    })

    return state
