"""
product_qa_skill.py — 商品问答技能

职责：回答商品材质、尺寸、参数、使用方法等问题。
      使用通用 Product QA Resolver，不依赖硬编码商品名。
      商品识别来自 data/products.json 的 name / aliases 字段。

Resolver 输出：
    {
        "matched_product": dict | None,
        "matched_product_name": str | None,
        "query_type": "size/material/price/suitability/care/color/general",
        "used_history": bool,
        "needs_clarification": bool,
        "needs_data_fallback": bool,
        "reason": str
    }
"""

from app.tools.local_product_tool import resolve_product, find_product_in_history
from app.tools.local_faq_tool import query_faq
from app.tools.mock_product_tool import get_mock_product_info


# ── Query Type Detection ──

_QUERY_RULES: list[tuple[list[str], str]] = [
    (["码数", "尺码", "尺寸", "大小", "几码", "多大", "均码"], "size"),
    (["材质", "面料", "什么料", "成分"], "material"),
    (["多少钱", "价格", "价位", "贵吗", "便宜"], "price"),
    (["适合", "适不适合", "多少岁", "送人", "我妈", "妈妈", "长辈", "中年", "通勤", "骑车", "户外", "日常穿", "送妈妈"], "suitability"),
    (["怎么洗", "洗涤", "保养", "能机洗吗", "清洗"], "care"),
    (["颜色", "黑色", "白色", "有哪些颜色", "什么颜色"], "color"),
    (["推荐", "介绍", "怎么样"], "general"),
]


def _detect_query_type(text: str) -> str:
    """通用问题类型识别。"""
    for keywords, qtype in _QUERY_RULES:
        if any(kw in text for kw in keywords):
            return qtype
    return "unknown"


# ── Follow-up detection ──

_FOLLOWUP_KEYWORDS = [
    "码数", "尺码", "码", "大小", "尺寸", "多大", "几码",
    "适合吗", "能穿吗", "能穿",
    "怎么洗", "怎么穿", "保养", "清洗",
    "还有别的吗", "还有什么",
    "这个呢", "那款呢", "那款",
    "什么颜色", "黑色", "颜色",
    "多少钱", "价格", "价位", "贵",
    "怎么用", "怎么安装",
]


# ── Answer Builder ──

def _build_reply(product: dict, query_type: str) -> str:
    """根据 query_type 从商品字段构建回复。"""
    name = product.get("name", "商品")

    if query_type == "size":
        sizes = product.get("sizes", [])
        if not sizes:
            return f"这款 {name} 的尺码信息暂未录入，建议补充商品资料后再回答。"
        return (
            f"这款 {name} 的尺码信息如下：\n"
            f"可选尺码：{' / '.join(sizes)}\n"
            f"版型为常规版，建议按平时尺码选购。\n"
            f"如果您不确定选哪个尺码，可以告诉我身高体重，我帮您参考。"
        )

    elif query_type == "material":
        material = product.get("material", "")
        if not material:
            return f"这款 {name} 的材质信息暂未录入，建议补充商品资料后再回答。"
        features = "、".join(product.get("features", []))
        scenes = "、".join(product.get("suitable_scenarios", ["日常"]))
        return (
            f"这款 {name} 的材质信息如下：\n"
            f"材质成分：{material}\n"
            f"特点：{features}\n"
            f"此材质适合{scenes}穿着。"
        )

    elif query_type == "price":
        price = product.get("price_range", "")
        if not price:
            return f"这款 {name} 的价格信息暂未录入，建议补充商品资料后再回答。"
        return f"这款 {name} 的价格区间为 {price}。具体价格可能因活动有所浮动。"

    elif query_type == "suitability":
        scenes = product.get("suitable_scenarios", [])
        if not scenes:
            return f"这款 {name} 的适用场景信息暂未录入，建议补充商品资料后再回答。"
        features = "、".join(product.get("features", []))
        return (
            f"这款 {name} 适合的场景：{'、'.join(scenes)}。\n"
            f"特点：{features}\n"
            f"如果您有具体的需求，可以再告诉我，我帮您进一步判断。"
        )

    elif query_type == "care":
        care = product.get("care_instructions", "")
        if not care:
            return f"这款 {name} 的保养信息暂未录入，建议补充商品资料后再回答。"
        return f"这款 {name} 的保养建议如下：\n{care}"

    elif query_type == "color":
        colors = product.get("colors", [])
        if not colors:
            return f"这款 {name} 的颜色信息暂未录入，建议补充商品资料后再回答。"
        return f"这款 {name} 可选颜色：{'、'.join(colors)}。需要了解更多颜色可以告诉我。"

    else:
        # general / unknown
        features = "、".join(product.get("features", []))
        scenes = "、".join(product.get("suitable_scenarios", ["日常"]))
        sizes = " / ".join(product.get("sizes", ["—"]))
        material = product.get("material", "—")
        price = product.get("price_range", "—")
        return (
            f"您咨询的商品信息如下：\n"
            f"商品名称：{name}\n"
            f"材质：{material}\n"
            f"尺码：{sizes}\n"
            f"特点：{features}\n"
            f"适用场景：{'、'.join(scenes)}\n"
            f"参考价格：{price}\n"
            f"（当前使用本地示例商品资料）\n"
            f"如果您需要了解更多信息，欢迎继续咨询。"
        )


def _needs_clarification() -> dict:
    """需要用户补充商品名称。"""
    return {
        "skill_result": {
            "action": "product_answer",
            "knowledge_source": "clarification",
            "message": "您想问的是哪款商品呢？可以告诉我商品名称或型号。",
        }
    }


def _mock_fallback(text: str) -> dict:
    """回退到稳定 mock 商品资料。"""
    product = get_mock_product_info()
    return {
        "skill_result": {
            "action": "product_answer",
            "knowledge_source": "mock_fallback",
            "product_info": product,
            "message": _build_reply(product, "general"),
        }
    }


# ── Main Entry ──

def run_product_qa_skill(state: dict) -> dict:
    """
    通用商品问答入口。

    优先级：
        0. state.explicit_product（LLM Semantic Parser 结果）优先
        1. 当前输入明确商品名 → resolve_product 直接匹配
        2. 当前输入无商品 → 尝试从 history 推断商品
        3. 商品确定 → state.query_type 优先，否则 _detect_query_type
        4. 从字段构建回复
        5. 字段缺失 → 提示资料未录入
        6. 完全无匹配 → 澄清或 fallback
    """
    text = state.get("user_message", "") or ""
    history = state.get("conversation_history", [])
    query_type = state.get("query_type") or _detect_query_type(text)

    # ── 第 0 步：LLM Semantic Parser 输出的 explicit_product ──
    product = None
    explicit = state.get("explicit_product")
    if explicit:
        pr = resolve_product(explicit)
        if pr.get("matched"):
            product = pr["matched_product"]

    # ── 第 1 步：当前输入明确商品 ──
    if not product:
        result = resolve_product(text)
        product = result.get("matched_product")

    used_history = False

    # ── 第 2 步：当前无商品，尝试 history ──
    if not product and history:
        history_result = find_product_in_history(history)
        product = history_result.get("matched_product")
        used_history = True

    # ── 第 3 步：无商品匹配 → 尝试 FAQ，再澄清 ──
    if not product:
        intent = state.get("intent")
        faq_result = query_faq(text, intent)
        if faq_result.get("matched"):
            return {
                "skill_result": {
                    "action": "product_answer",
                    "knowledge_source": "local_faq",
                    "matched_faq": faq_result["matched_faq"],
                    "message": faq_result["matched_faq"]["answer"],
                }
            }
        return _needs_clarification()

    # ── 第 4 步：构建回复 ──
    message = _build_reply(product, query_type)

    return {
        "skill_result": {
            "action": "product_answer",
            "knowledge_source": "local_products",
            "matched_product": product,
            "query_type": query_type,
            "used_history": used_history,
            "message": message,
        }
    }
