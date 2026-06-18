"""
recommendation_skill.py — 商品推荐技能

职责：根据用户需求做售前推荐。
      优先从本地知识库（products.json）读取商品列表推荐。
"""

from app.tools.local_product_tool import query_product
from app.tools.mock_product_tool import get_mock_product_info


def _load_all_products() -> list[dict]:
    """加载全部商品信息（用于推荐列表）。"""
    import json, os
    path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "products.json"))
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _build_recommendation(products: list[dict]) -> str:
    """构建推荐回复。"""
    lines = ["根据您的需求，我为您推荐以下商品："]
    for p in products[:3]:
        name = p.get("name", "")
        price = p.get("price_range", "")
        features = "、".join(p.get("features", [])[:3])
        scene = "、".join(p.get("suitable_scene", []))
        lines.append(f"\n▪ {name}（{price}）")
        lines.append(f"  特点：{features}")
        if scene:
            lines.append(f"  适用：{scene}")
    lines.append("\n（当前使用本地示例商品资料）")
    lines.append("如果您需要更精准的推荐，可以告诉我使用场景、预算和尺码。")
    return "\n".join(lines)


def run_recommendation_skill(state: dict) -> dict:
    """执行商品推荐，优先从本地商品知识库推荐。"""
    text = state.get("user_message", "") or ""
    products = _load_all_products()

    # 优先按用户输入匹配
    result = query_product(text)
    if result.get("matched") and result["matched_product"]:
        product = result["matched_product"]
        return {
            "skill_result": {
                "action": "recommendation",
                "knowledge_source": "local_products",
                "recommended_products": [product],
                "message": _build_recommendation([product]),
            }
        }

    # 没有精确匹配：推荐全部商品
    if products:
        return {
            "skill_result": {
                "action": "recommendation",
                "knowledge_source": "local_products",
                "recommended_products": products[:3],
                "message": _build_recommendation(products),
            }
        }

    # 回退：保守说明
    return {
        "skill_result": {
            "action": "recommendation_demo",
            "knowledge_source": "mock_fallback",
            "message": (
                "我可以帮您推荐。当前 Demo 暂未接入真实商品库，"
                "我先根据常见需求给您一个保守建议：如果是夏季通勤/"
                "骑车，可以优先考虑轻薄透气、防晒等级 UPF50+ 的防晒衣；"
                "如果是运动场景，可以选择轻量运动外套。"
                "您也可以补充预算、尺码和使用场景，我再进一步推荐。"
            ),
        }
    }
