"""
classify_intent.py — 意图识别节点

职责：通过关键词匹配识别用户意图，可选由 LLM Semantic Parser 增强。
      第一版用关键词规则，后续升级为真实 LLM。
      Phase 7 新增：图文场景下拼接 multimodal_analysis 增强匹配。
      Phase 10.19 新增：LLM Semantic Parser（默认关闭）。
"""

from datetime import datetime

from app.llm.provider_factory import get_llm_provider
from app.llm.semantic_parser import (
    build_parser_payload,
    should_enable,
    validate_semantic_parse,
)
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
_INTENT_RULES = [
    (INTENT_HUMAN_REQUEST, 0.95, ["人工", "真人", "客服", "转人工", "我要找人"]),
    (INTENT_COMPLAINT, 0.95, ["投诉", "差评", "骗子", "垃圾", "不满意"]),
    (INTENT_REFUND_REQUEST, 0.90, ["退款", "退钱", "不想要了", "质量太差", "质量太差了", "退货退款"]),
    (INTENT_EXCHANGE_REQUEST, 0.85, ["换货", "换一个", "换个", "尺码不合适", "换码", "换颜色"]),
    (INTENT_LOGISTICS_QUESTION, 0.80, ["快递", "物流", "到哪了", "什么时候到", "发货", "单号"]),
    (INTENT_RECOMMENDATION, 0.75, ["推荐", "哪个好", "适合我吗", "怎么选", "买哪款"]),
    (INTENT_PRODUCT_QUESTION, 0.70, ["材质", "尺寸", "参数", "适合", "怎么用", "怎么安装", "怎么洗", "保养", "清洗", "码数", "码", "尺码", "颜色", "款式", "质量", "哪个颜色", "好不好", "多少钱", "价格", "价位", "贵吗"]),
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


def _run_semantic_parser(state: CustomerServiceState, rule_intent: str, rule_confidence: float) -> dict:
    """调用 LLM Semantic Parser 增强 intent 理解。"""
    payload = build_parser_payload(state)
    try:
        provider = get_llm_provider()
        result = provider.parse_semantic(payload)
        if not result.get("success"):
            return {"intent_source": "fallback", "intent": rule_intent, "confidence": rule_confidence}
        validated = validate_semantic_parse(result, {**state, "intent": rule_intent})
        if validated.get("fallback"):
            return {"intent_source": "fallback", "intent": rule_intent, "confidence": rule_confidence}
        return {
            "intent_source": "llm",
            "intent": validated["intent"],
            "confidence": validated.get("confidence", rule_confidence),
            "explicit_product": validated.get("explicit_product"),
            "query_type": validated.get("query_type"),
            "user_signal": validated.get("user_signal"),
        }
    except Exception as e:
        print(f"[semantic_parser] Error: {e}")
        return {"intent_source": "fallback", "intent": rule_intent, "confidence": rule_confidence}


def classify_intent(state: CustomerServiceState) -> dict:
    """
    通过关键词匹配识别用户意图。

    读取字段：user_message, multimodal_analysis（图文增强）
    写入字段：intent, intent_confidence, logs, intent_source, explicit_product, query_type, user_signal

    Args:
        state: 当前状态

    Returns:
        包含 intent, intent_confidence, logs, intent_source, explicit_product, query_type, user_signal 的部分 state dict
    """
    text = _get_combined_text(state)
    rule_intent = INTENT_SMALLTALK
    rule_confidence = 0.3

    if text:
        for intent_val, conf, keywords in _INTENT_RULES:
            if any(kw in text for kw in keywords):
                rule_intent = intent_val
                rule_confidence = conf
                break

    intent = rule_intent
    confidence = rule_confidence
    intent_source = "rule"
    explicit_product = None
    query_type = None
    user_signal = None

    # Semantic Parser（默认关闭）
    if should_enable():
        sp_result = _run_semantic_parser(state, rule_intent, rule_confidence)
        if sp_result.get("intent_source") == "llm":
            intent = sp_result["intent"]
            confidence = sp_result.get("confidence", rule_confidence)
            intent_source = "llm"
            explicit_product = sp_result.get("explicit_product")
            query_type = sp_result.get("query_type")
            user_signal = sp_result.get("user_signal")
        # fallback 时使用规则结果

    updated_logs = list(state["logs"])
    updated_logs.append({
        "node": "classify_intent",
        "summary": f"intent={intent}, confidence={confidence}, source={intent_source}",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {
        "intent": intent,
        "intent_confidence": confidence,
        "intent_source": intent_source,
        "explicit_product": explicit_product,
        "query_type": query_type,
        "user_signal": user_signal,
        "logs": updated_logs,
    }
