"""
classify_emotion.py — 情绪识别节点

职责：通过关键词匹配识别用户情绪。
      第一版用关键词规则，后续升级为真实 LLM。
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

# 关键词规则，优先级从高到低
# 每条：(emotion值, 评分, [关键词列表])
# 优先级说明：angry > urgent > anxious > disappointed > neutral
# emotion_score > 0.85 时会触发转人工（Phase 5 中实现）
_EMOTION_RULES = [
    (EMOTION_ANGRY, 0.90, ["垃圾", "骗子", "投诉", "太差了", "气死了", "什么态度", "差评"]),
    (EMOTION_URGENT, 0.80, ["急", "马上", "立刻", "现在就要", "今天必须"]),
    (EMOTION_ANXIOUS, 0.65, ["怎么还没到", "等很久了", "担心", "有没有问题", "什么时候处理"]),
    (EMOTION_DISAPPOINTED, 0.60, ["失望", "不满意", "不好用", "和想象不一样"]),
]


def classify_emotion(state: CustomerServiceState) -> dict:
    """
    通过关键词匹配识别用户情绪。

    读取字段：user_message
    写入字段：emotion, emotion_score, logs

    Args:
        state: 当前状态

    Returns:
        包含 emotion, emotion_score, logs 的部分 state dict
    """
    text = state["user_message"]
    emotion = EMOTION_NEUTRAL
    score = 0.0  # 未命中任何关键词时，中性情绪 + 0 分

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
