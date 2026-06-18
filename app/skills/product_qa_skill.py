"""
product_qa_skill.py — 商品问答技能

职责：回答商品材质、尺寸、参数、使用方法等问题。
      调用 mock_product_tool 获取商品信息。
"""

from app.tools.mock_product_tool import get_mock_product_info


def run_product_qa_skill(state: dict) -> dict:
    """执行商品问答，返回商品信息。"""
    product = get_mock_product_info()
    return {
        "skill_result": {
            "action": "product_answer",
            "product_info": product,
            "message": "已查询商品基础信息",
        }
    }
