"""
analyze_text.py — 文本分析节点

职责: 对用户文本做 mock 分析，不调用真实 LLM。
      只在有文本输入时生成 text_analysis，纯图片时跳过。
"""

from datetime import datetime

from app.state.customer_state import (
    MODALITY_IMAGE_ONLY,
    MODALITY_TEXT_ONLY,
    MODALITY_TEXT_WITH_IMAGE,
    CustomerServiceState,
)


def analyze_text(state: CustomerServiceState) -> dict:
    """
    对用户文本做 mock 分析。

    读取字段: user_message, modality
    写入字段: text_analysis, logs

    Rules:
        - modality 为 text_only 或 text_with_image 且有文本 → 生成 text_analysis
        - modality 为 image_only 或 unknown → text_analysis = None

    Args:
        state: 当前状态

    Returns:
        包含 text_analysis 和 logs 更新的部分 state dict
    """
    modality = state["modality"]
    user_msg = state["user_message"]
    text_analysis = None
    summary = ""

    if modality in (MODALITY_TEXT_ONLY, MODALITY_TEXT_WITH_IMAGE) and user_msg:
        text_analysis = f"用户输入了一段文本，内容是：{user_msg}"
        summary = "生成文本分析完成"
    elif modality == MODALITY_IMAGE_ONLY:
        summary = "纯图片输入，跳过文本分析"
    else:
        summary = f"模态为 {modality}，跳过文本分析"

    updated_logs = list(state["logs"])
    updated_logs.append({
        "node": "analyze_text",
        "summary": summary,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {"text_analysis": text_analysis, "logs": updated_logs}
