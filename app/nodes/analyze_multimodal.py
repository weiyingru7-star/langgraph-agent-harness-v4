"""
analyze_multimodal.py — 多模态分析节点

职责：当输入为 text_with_image 时，调用 mock_multimodal_tool 生成图文分析。
      第一版不接真实多模态模型。
"""

from datetime import datetime

from app.state.customer_state import (
    MODALITY_TEXT_WITH_IMAGE,
    CustomerServiceState,
)
from app.tools.mock_multimodal_tool import analyze_mock_image_with_text


def analyze_multimodal(state: CustomerServiceState) -> dict:
    """
    分析图文混合输入。

    读取字段：session_id, user_message, image_url, image_base64, modality
    写入字段：multimodal_analysis, logs

    Args:
        state: 当前状态

    Returns:
        包含 multimodal_analysis 和 logs 的部分 state dict
    """
    modality = state["modality"]

    if modality != MODALITY_TEXT_WITH_IMAGE:
        # 非图文场景，跳过分析
        updated_logs = list(state["logs"])
        updated_logs.append({
            "node": "analyze_multimodal",
            "summary": f"跳过分析（modality={modality}）",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })
        return {"multimodal_analysis": None, "logs": updated_logs}

    # 确定用于分析的文本（decide_modality 已在回溯场景中写回 user_message）
    text = state["user_message"] or ""

    # 调用 mock 多模态 tool
    result = analyze_mock_image_with_text(
        user_message=text,
        image_url=state["image_url"],
        image_base64=state["image_base64"],
    )

    updated_logs = list(state["logs"])
    updated_logs.append({
        "node": "analyze_multimodal",
        "summary": f"调用 mock_multimodal_tool，confidence={result['confidence']}",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {"multimodal_analysis": result, "logs": updated_logs}
