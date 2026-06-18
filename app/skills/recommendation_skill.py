"""
recommendation_skill.py — 商品推荐技能

职责：根据用户需求做售前推荐。
      调用 mock_product_tool 获取推荐商品信息。
"""

from app.tools.mock_product_tool import get_mock_product_info


def run_recommendation_skill(state: dict) -> dict:
    """执行商品推荐，返回推荐信息。"""
    product = get_mock_product_info()
    return {
        "skill_result": {
            "action": "recommendation",
            "product_info": product,
            "message": "已根据用户需求生成推荐信息",
        }
    }
