"""
product_qa_skill.py — 商品问答技能

职责：回答商品材质、尺寸、参数、使用方法等问题。
      优先从本地知识库（products.json / faq.json）查询，
      未命中时回退稳定 mock 商品资料。
"""

from app.tools.local_faq_tool import query_faq
from app.tools.local_product_tool import query_product, find_product_by_name
from app.tools.mock_product_tool import get_mock_product_info


def _detect_query_type(text: str) -> str:
    """检测当前问题类型。"""
    if any(w in text for w in ["码数", "尺码", "码", "大小", "尺寸", "多大", "几码"]):
        return "size"
    if any(w in text for w in ["材质", "面料", "什么料", "成分"]):
        return "material"
    if any(w in text for w in ["适合", "能穿", "可以穿", "年龄段", "岁"]):
        return "suitability"
    if any(w in text for w in ["怎么洗", "洗涤", "保养", "清洗"]):
        return "care"
    if any(w in text for w in ["多少钱", "价格", "价位", "贵"]):
        return "price"
    if any(w in text for w in ["怎么用", "怎么穿", "怎么安装"]):
        return "usage"
    return "general"


def _build_reply_from_product(product: dict, text: str) -> str:
    """根据问题类型从商品 dict 构建针对性回复。"""
    name = product.get("name") or product.get("product_name", "商品")

    if any(w in text for w in ["码数", "尺码", "码", "大小", "尺寸"]):
        sizes = " / ".join(product.get("sizes", ["—"]))
        return (
            f"这款 {name} 的尺码信息如下：\n"
            f"可选尺码：{sizes}\n"
            f"版型为常规版，建议按平时尺码选购。\n"
            f"如果您不确定选哪个尺码，可以告诉我身高体重，我帮您参考。"
        )
    elif any(w in text for w in ["适合", "能穿", "可以穿", "推荐", "年龄段"]):
        people = product.get("suitable_people", "适合各年龄段穿着。")
        scenes = "、".join(product.get("suitable_scene", ["日常"]))
        features = "、".join(product.get("features", []))
        return (
            f"这款 {name} {people}\n"
            f"特点：{features}\n"
            f"适用场景：{scenes}\n"
            f"如果您有具体的场景或需求，可以再问我进一步判断。"
        )
    elif any(w in text for w in ["材质", "面料", "什么料", "成分", "质量"]):
        material = product.get("material", "—")
        features = "、".join(product.get("features", []))
        scenes = "、".join(product.get("suitable_scene", ["日常"]))
        return (
            f"这款 {name} 的材质信息如下：\n"
            f"材质成分：{material}\n"
            f"特点：{features}\n"
            f"此材质适合{scenes}穿着。"
        )
    elif any(w in text for w in ["怎么用", "怎么穿", "怎么洗", "保养", "清洗"]):
        care = product.get("care_instructions", "建议参考商品标签说明。")
        scenes = "、".join(product.get("suitable_scene", ["日常"]))
        return (
            f"这款 {name} 的使用与保养建议：\n"
            f"{care}\n"
            f"适合{scenes}穿着，日常保养方便。"
        )
    elif any(w in text for w in ["多少钱", "价格", "价位", "贵"]):
        price = product.get("price_range", "—")
        return (f"这款 {name} 的价格区间为 {price}。具体价格可能因活动有所浮动。")
    else:
        material = product.get("material", "—")
        sizes = " / ".join(product.get("sizes", ["—"]))
        features = "、".join(product.get("features", []))
        scenes = "、".join(product.get("suitable_scene", ["日常"]))
        price = product.get("price_range", "—")
        return (
            f"您咨询的商品信息如下：\n"
            f"商品名称：{name}\n"
            f"材质：{material}\n"
            f"尺码：{sizes}\n"
            f"特点：{features}\n"
            f"适用场景：{scenes}\n"
            f"参考价格：{price}\n"
            f"（当前使用本地示例商品资料）\n"
            f"如果您需要了解更多信息，欢迎继续咨询。"
        )


def _mock_fallback_reply(text: str) -> dict:
    """回退到稳定 mock 商品资料。"""
    product = get_mock_product_info()
    return {
        "skill_result": {
            "action": "product_answer",
            "knowledge_source": "mock_fallback",
            "product_info": product,
            "message": _build_reply_from_product(product, text),
        }
    }


# 追问关键词列表
_FOLLOWUP_KEYWORDS = [
    "码数", "尺码", "码", "大小", "尺寸", "多大",
    "适合吗", "能穿吗", "能穿",
    "怎么洗", "怎么穿", "保养", "清洗",
    "还有别的吗", "还有什么",
    "这个呢", "那款呢", "那款",
    "什么颜色", "黑色", "颜色",
    "多少钱", "价格", "价位", "贵",
    "怎么用", "怎么安装",
]

# 本地商品名称列表（用于从历史中匹配）
_KNOWN_PRODUCTS = ["UPF50+ 轻薄防晒衣", "轻量运动外套", "可折叠遮阳帽"]


def _find_product_in_history(history: list) -> str | None:
    """从对话历史中查找最后一次提到的商品名。"""
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            for name in _KNOWN_PRODUCTS:
                if name in content:
                    return name
    return None


def _maybe_enrich_with_history(text: str, state: dict) -> str:
    """
    只有在当前用户消息没有明确提到商品名时，
    才从 conversation_history 中取最近商品名增强文本。
    """
    # 先检查当前消息是否已有明确商品名
    explicit = find_product_by_name(text)
    if explicit.get("matched"):
        return text  # 当前消息已有商品名，不覆盖
    # 没有明确商品名：尝试从历史推断
    if not any(kw in text for kw in _FOLLOWUP_KEYWORDS):
        return text
    history = state.get("conversation_history", [])
    if not history:
        return text
    product_name = _find_product_in_history(history)
    if product_name:
        return f"{product_name} {text}"
    return text


def run_product_qa_skill(state: dict) -> dict:
    """执行商品问答，优先从本地知识库查询。

    优先级：
        1. 当前 user_message 明确包含商品名 → 直接回答该商品
        2. 从 history 推断商品 + 商品详细
        3. 从 history 推断商品 + FAQ
        4. fallback mock
    """
    original_text = state.get("user_message", "") or ""
    query_type = _detect_query_type(original_text)

    # ── 第 1 步：当前消息是否明确包含商品名 ──
    explicit = find_product_by_name(original_text)
    if explicit.get("matched"):
        product = explicit["matched_product"]
        return {
            "skill_result": {
                "action": "product_answer",
                "knowledge_source": "local_products",
                "matched_product": product,
                "message": _build_reply_from_product(product, original_text),
            }
        }

    # ── 第 2 步：从 history 推断商品 ──
    enriched = _maybe_enrich_with_history(original_text, state)
    if enriched != original_text:
        # history 提供了商品上下文
        product_result = find_product_by_name(enriched)
        if product_result.get("matched"):
            product = product_result["matched_product"]
            return {
                "skill_result": {
                    "action": "product_answer",
                    "knowledge_source": "local_products",
                    "matched_product": product,
                    "message": _build_reply_from_product(product, enriched),
                }
            }

    # ── 第 3 步：FAQ ──
    intent = state.get("intent")
    faq_result = query_faq(original_text, intent)
    if faq_result.get("matched"):
        return {
            "skill_result": {
                "action": "product_answer",
                "knowledge_source": "local_faq",
                "matched_faq": faq_result["matched_faq"],
                "message": faq_result["matched_faq"]["answer"],
            }
        }

    # ── 第 4 步：商品知识库 ──
    product_result = query_product(enriched)
    if product_result.get("matched"):
        product = product_result["matched_product"]
        return {
            "skill_result": {
                "action": "product_answer",
                "knowledge_source": "local_products",
                "matched_product": product,
                "message": _build_reply_from_product(product, enriched),
            }
        }

    # ── 第 5 步：回退 mock ──
    return _mock_fallback_reply(enriched)
