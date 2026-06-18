"""
product_qa_skill.py — 商品问答技能

职责：回答商品材质、尺寸、参数、使用方法等问题。
      优先从本地知识库（products.json / faq.json）查询，
      未命中时回退稳定 mock 商品资料。
"""

from app.tools.local_faq_tool import query_faq
from app.tools.local_product_tool import query_product
from app.tools.mock_product_tool import get_mock_product_info


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


def run_product_qa_skill(state: dict) -> dict:
    """执行商品问答，优先从本地知识库查询。"""
    text = state.get("user_message", "") or ""

    # 1. 查 FAQ
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

    # 2. 查商品知识库
    product_result = query_product(text)
    if product_result.get("matched"):
        product = product_result["matched_product"]
        return {
            "skill_result": {
                "action": "product_answer",
                "knowledge_source": "local_products",
                "matched_product": product,
                "message": _build_reply_from_product(product, text),
            }
        }

    # 3. 回退 mock
    return _mock_fallback_reply(text)
