"""
semantic_parser.py — LLM 语义解析器。

在 classify_intent 规则匹配后，可选调用 LLM 辅助理解用户语义。
输出结构化 JSON，Code 校验后用于增强路由。

默认关闭（LLM_ENABLE_SEMANTIC_PARSER=false）。
"""

import json
import os
from typing import Any, Dict, List, Optional

# 允许的 intent 枚举
ALLOWED_INTENTS = [
    "product_question", "recommendation", "refund_request",
    "logistics_question", "exchange_request", "complaint",
    "human_request", "smalltalk", "knowledge_question", "unknown",
]

# 允许的 query_type 枚举
ALLOWED_QUERY_TYPES = [
    "size", "material", "price", "suitability", "care", "color",
    "general", "policy", "logistics", "comparison", "unknown",
]

# 强规则关键词——无论 LLM 说什么，这些词必须保持高优先级
_HARD_RULES: List[tuple[List[str], str, float]] = [
    (["退款", "退钱", "退货退款", "不想要了"], "refund_request", 0.90),
    (["投诉", "差评", "骗子", "垃圾"], "complaint", 0.95),
    (["人工", "真人", "客服", "转人工", "我要找人"], "human_request", 0.95),
    (["换货", "换一个", "换个", "尺码不合适"], "exchange_request", 0.85),
    (["快递", "物流", "到哪了", "发货", "单号"], "logistics_question", 0.80),
]

_USER_SIGNALS = {
    "positive_interest": ["不错", "好看", "可以", "喜欢", "适合"],
    "purchase_interest": ["买", "下单", "多少钱", "价格"],
    "negative_feedback": ["太差", "不好", "不行", "失望"],
    "complaint": ["投诉", "举报", "差评"],
    "just_chat": ["你好", "在吗", "谢谢"],
}


def build_parser_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    """构建 Sematic Parser 的 payload。"""
    from app.tools.local_product_tool import get_all_products
    products = get_all_products()
    available = []
    for p in products:
        entry = {"name": p.get("name", ""), "aliases": p.get("aliases", [])}
        available.append(entry)

    return {
        "user_message": state.get("user_message", ""),
        "conversation_history": state.get("conversation_history", []),
        "rule_intent": state.get("intent", "smalltalk"),
        "emotion": state.get("emotion", "neutral"),
        "available_products": available,
        "safety_rules": [
            "不得将退款/投诉/人工请求降级为闲聊",
            "不得编造商品信息",
            "不允许的商品名返回 null",
            "如果用户当前明确提到某个商品，explicit_product 必须填写该商品",
        ],
    }


def validate_semantic_parse(result: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    校验 LLM 语义解析结果。

    返回修正后的结果，或 fallback 到规则。
    """
    text = state.get("user_message", "") or ""
    validated = {
        "intent": result.get("intent", "unknown"),
        "explicit_product": result.get("explicit_product"),
        "query_type": result.get("query_type", "unknown"),
        "use_history": result.get("use_history", False),
        "user_signal": result.get("user_signal", "unknown"),
        "confidence": result.get("confidence", 0.0),
        "reason": result.get("reason", ""),
    }

    # 1. intent 必须在允许枚举内
    if validated["intent"] not in ALLOWED_INTENTS:
        return {"fallback": True, "reason": "intent 不在允许枚举中"}

    # 2. query_type 必须在允许枚举内
    if validated["query_type"] not in ALLOWED_QUERY_TYPES:
        validated["query_type"] = "unknown"

    # 3. confidence < 0.6 → fallback
    if validated["confidence"] < 0.6:
        return {"fallback": True, "reason": f"置信度过低 ({validated['confidence']})"}

    # 4. 强规则覆盖：退款/投诉/人工不能降级
    for keywords, hard_intent, _ in _HARD_RULES:
        if any(kw in text for kw in keywords):
            if hard_intent in ("refund_request", "complaint", "human_request"):
                if validated["intent"] not in (hard_intent, hard_intent):
                    # 强规则不允许降级
                    validated["intent"] = hard_intent
                    validated["reason"] += f"[强规则覆盖为 {hard_intent}]"
                    break

    # 5. explicit_product 如果填写，必须在 available_products 中存在
    if validated["explicit_product"]:
        from app.tools.local_product_tool import resolve_product
        pr = resolve_product(validated["explicit_product"])
        if not pr.get("matched"):
            # 尝试在 name/aliases 中匹配
            from app.tools.local_product_tool import get_all_products
            found = False
            for p in get_all_products():
                if p["name"] == validated["explicit_product"]:
                    found = True
                    break
                if validated["explicit_product"] in p.get("aliases", []):
                    validated["explicit_product"] = p["name"]
                    found = True
                    break
            if not found:
                validated["explicit_product"] = None
                validated["reason"] += "[商品不在数据库中，已清除]"

    validated["fallback"] = False
    validated["reason"] = validated.get("reason", "")
    return validated


def should_enable() -> bool:
    """是否启用 Semantic Parser。"""
    provider = os.getenv("LLM_PROVIDER", "mock")
    enabled = os.getenv("LLM_ENABLE_SEMANTIC_PARSER", "false") == "true"
    return enabled and (provider in ("deepseek", "mock"))


# ══════════════════════════════════════════
#  Prompt 模板
# ══════════════════════════════════════════

SEMANTIC_PARSE_PROMPT = """你是一个电商客服语义理解助手。你的职责：

1. 分析用户输入文本，输出结构化语义结果。
2. 可以引用对话历史来理解代词（这个、那个、第二个、它）。
3. 如果用户当前明确提到商品名，explicit_product 必须填写该商品。
4. 不得将退款/投诉/转人工请求降级为闲聊或商品咨询。
5. 不得编造商品信息。
6. 输出必须是 JSON 格式，不要额外说明。

输出 JSON 结构：
{
  "intent": "product_question | recommendation | refund_request | logistics_question | exchange_request | complaint | human_request | smalltalk | unknown",
  "explicit_product": "商品完整名称" 或 null,
  "query_type": "size | material | price | suitability | care | color | general | policy | logistics | unknown",
  "use_history": true/false,
  "user_signal": "positive_interest | purchase_interest | negative_feedback | complaint | just_chat | unknown",
  "confidence": 0.0,
  "reason": "简要分析说明"
}"""
