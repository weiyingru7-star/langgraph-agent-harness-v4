"""
mock_order_tool.py — 订单查询 Mock

职责：模拟查询外部电商系统的订单数据。第一版不接真实 API。
      Tool 只负责提供外部数据，不负责业务决策。
"""


def get_mock_order_info() -> dict:
    """返回 mock 订单和物流信息，用于物流查询。"""
    return {
        "order_id": "ORD-20240101-001",
        "status": "已发货",
        "tracking_no": "SF1234567890",
        "eta": "预计明天到达",
        "items": [{"name": "经典款运动鞋", "quantity": 1}],
    }
