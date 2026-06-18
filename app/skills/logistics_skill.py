"""
logistics_skill.py — 物流查询技能

职责：查询 mock 物流信息。
      调用 mock_order_tool 获取订单和物流数据。
"""

from app.tools.mock_order_tool import get_mock_order_info


def run_logistics_skill(state: dict) -> dict:
    """查询 mock 物流信息。"""
    order = get_mock_order_info()
    return {
        "skill_result": {
            "action": "logistics_query",
            "order_info": order,
            "message": "已查询 mock 物流信息",
        }
    }
