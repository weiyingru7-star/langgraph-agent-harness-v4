"""
classify_stage.py — 客户阶段识别节点

职责：根据 intent（和 user_message 辅助）推导客户所处阶段。
      pre_sale / in_sale / after_sale / unknown
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
    STAGE_AFTER_SALE,
    STAGE_IN_SALE,
    STAGE_PRE_SALE,
    STAGE_UNKNOWN,
    CustomerServiceState,
)

# 售后关键词：用于 human_request 时判断是否属于售后问题
_AFTER_SALE_KEYWORDS = ["退款", "投诉", "质量", "售后", "换货", "退货"]


def classify_stage(state: CustomerServiceState) -> dict:
    """
    根据 intent 推导客户阶段。

    读取字段：user_message, intent
    写入字段：customer_stage, logs

    映射规则：
        - product_question / recommendation → pre_sale
        - logistics_question → in_sale
        - refund_request / exchange_request / complaint → after_sale
        - human_request：看 user_message 是否包含售后关键词
        - smalltalk / 其他 → unknown

    Args:
        state: 当前状态

    Returns:
        包含 customer_stage 和 logs 的部分 state dict
    """
    intent = state["intent"]
    stage = STAGE_UNKNOWN

    if intent == INTENT_PRODUCT_QUESTION or intent == INTENT_RECOMMENDATION:
        stage = STAGE_PRE_SALE
    elif intent == INTENT_LOGISTICS_QUESTION:
        stage = STAGE_IN_SALE
    elif intent == INTENT_REFUND_REQUEST or intent == INTENT_EXCHANGE_REQUEST or intent == INTENT_COMPLAINT:
        stage = STAGE_AFTER_SALE
    elif intent == INTENT_HUMAN_REQUEST:
        text = state["user_message"]
        if any(kw in text for kw in _AFTER_SALE_KEYWORDS):
            stage = STAGE_AFTER_SALE
        else:
            stage = STAGE_UNKNOWN
    # smalltalk 和其他情况保持 unknown

    updated_logs = list(state["logs"])
    updated_logs.append({
        "node": "classify_stage",
        "summary": f"customer_stage={stage}",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {"customer_stage": stage, "logs": updated_logs}
