"""
decide_modality.py — 模态判断节点

职责: 根据 user_message / image_url / image_base64 判断输入类型。
      此节点是纯代码判断，不调用 LLM。
"""

from datetime import datetime

from app.state.customer_state import (
    MODALITY_IMAGE_ONLY,
    MODALITY_TEXT_ONLY,
    MODALITY_TEXT_WITH_IMAGE,
    MODALITY_UNKNOWN,
    CustomerServiceState,
)


def decide_modality(state: CustomerServiceState) -> dict:
    """
    判断输入模态类型。

    读取字段: user_message, image_url, image_base64
    写入字段: modality, logs

    Rules:
        - 有文字、无图片 → text_only
        - 无文字、有图片 → image_only
        - 有文字、有图片 → text_with_image
        - 都无           → unknown

    Args:
        state: 当前状态

    Returns:
        包含 modality 和 logs 更新的部分 state dict
    """
    user_msg = state["user_message"]
    has_image = bool(state["image_url"] or state["image_base64"])

    if user_msg and has_image:
        modality = MODALITY_TEXT_WITH_IMAGE
        desc = "有文字、有图片"
    elif user_msg:
        modality = MODALITY_TEXT_ONLY
        desc = "有文字、无图片"
    elif has_image:
        modality = MODALITY_IMAGE_ONLY
        desc = "无文字、有图片"
    else:
        modality = MODALITY_UNKNOWN
        desc = "无文字、无图片"

    updated_logs = list(state["logs"])
    updated_logs.append({
        "node": "decide_modality",
        "summary": f"判断为 {modality}（{desc}）",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {"modality": modality, "logs": updated_logs}
