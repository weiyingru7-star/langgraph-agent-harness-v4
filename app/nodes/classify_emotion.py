"""
classify_emotion.py — 情绪识别节点

职责：通过关键词匹配识别用户情绪。
      第一版用关键词规则，后续升级为真实 LLM。
      Phase 7 新增：图文场景下拼接 multimodal_analysis 增强匹配。
"""

from datetime import datetime

from app.state.customer_state import (
    EMOTION_ANGRY,
    EMOTION_ANXIOUS,
    EMOTION_DISAPPOINTED,
    EMOTION_NEUTRAL,
    EMOTION_URGENT,
    CustomerServiceState,
)

_EMOTION_RULES = [
    (EMOTION_ANGRY, 0.90, ["垃圾", "骗子", "投诉", "太差了", "气死了", "什么态度", "差评"]),
    (EMOTION_URGENT, 0.80, ["急", "马上", "立刻", "现在就要", "今天必须"]),
    (EMOTION_ANXIOUS, 0.65, ["怎么还没到", "等很久了", "担心", "有没有问题", "什么时候处理"]),
    (EMOTION_DISAPPOINTED, 0.60, ["失望", "不满意", "不好用", "和想象不一样"]),
]


def _get_combined_text(state: CustomerServiceState) -> str:
    """获取用于关键词匹配的文本。"""
    text = state["user_message"]
    multimodal = state.get("multimodal_analysis")
    if multimodal:
        need = multimodal.get("combined_need", "") if isinstance(multimodal, dict) else ""
        if need:
            text = text + " " + need
    return text


def classify_emotion(state: CustomerServiceState) -> dict:
    """
    通过关键词匹配识别用户情绪。

    读取字段：user_message, multimodal_analysis（图文增强）
    写入字段：emotion, emotion_score, logs

    Args:
        state: 当前状态

    Returns:
        包含 emotion, emotion_score, logs 的部分 state dict
    """
    text = _get_combined_text(state)
    emotion = EMOTION_NEUTRAL
    score = 0.0

    if text:
        for emotion_val, score_val, keywords in _EMOTION_RULES:
            if any(kw in text for kw in keywords):
                emotion = emotion_val
                score = score_val
                break

    updated_logs = list(state["logs"])
    updated_logs.append({
        "node": "classify_emotion",
        "summary": f"emotion={emotion}, score={score}",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {"emotion": emotion, "emotion_score": score, "logs": updated_logs}
