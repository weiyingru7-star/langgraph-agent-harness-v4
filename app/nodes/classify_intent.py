"""
classify_intent.py — 意图识别节点

职责：通过关键词匹配识别用户意图。
      第一版用关键词规则，后续升级为真实 LLM。
"""

from datetime import datetime

from app.state.customer_state import (
    INTENT_COMPLAINT,
    INTENT_EXCHANGE_REQUEST,
    INTENT_HUMAN_REQUEST,
    INTENT_LOGISTICS_QUESTION,
    INTENT_PRODUCT_QUESTION,
    INTENT_RECOMMENDATION,
    INTENT_REFUND_REQUEST,
    INTENT_SMALLTALK,
    CustomerServiceState,
)

# 关键词规则，优先级从高到低
# 每条：(intent值, 置信度, [关键词列表])
# 优先级说明：
#   human_request > complaint > refund_request > exchange_request
#   > logistics_question > recommendation > product_question
# 未命中任何关键词时，默认返回 smalltalk + 低置信度 0.3
_INTENT_RULES = [
    (INTENT_HUMAN_REQUEST, 0.95, ["人工", "真人", "客服", "转人工", "我要找人"]),
    (INTENT_COMPLAINT, 0.95, ["投诉", "差评", "骗子", "垃圾", "不满意"]),
    (INTENT_REFUND_REQUEST, 0.90, ["退款", "退钱", "不想要了", "质量太差", "质量太差了", "退货退款"]),
    (INTENT_EXCHANGE_REQUEST, 0.85, ["换货", "换一个", "换个", "尺码不合适", "换码", "换颜色"]),
    (INTENT_LOGISTICS_QUESTION, 0.80, ["快递", "物流", "到哪了", "什么时候到", "发货", "单号"]),
    (INTENT_RECOMMENDATION, 0.75, ["推荐", "哪个好", "适合我吗", "怎么选", "买哪款"]),
    (INTENT_PRODUCT_QUESTION, 0.70, ["材质", "尺寸", "参数", "适合", "怎么用", "怎么安装"]),
]


def classify_intent(state: CustomerServiceState) -> dict:
    """
    通过关键词匹配识别用户意图。

    读取字段：user_message
    写入字段：intent, intent_confidence, logs

    Args:
        state: 当前状态

    Returns:
        包含 intent, intent_confidence, logs 的部分 state dict
    """
    text = state["user_message"]
    intent = INTENT_SMALLTALK
    confidence = 0.3

    if text:
        for intent_val, conf, keywords in _INTENT_RULES:
            if any(kw in text for kw in keywords):
                intent = intent_val
                confidence = conf
                break

    updated_logs = list(state["logs"])
    updated_logs.append({
        "node": "classify_intent",
        "summary": f"intent={intent}, confidence={confidence}",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {"intent": intent, "intent_confidence": confidence, "logs": updated_logs}
