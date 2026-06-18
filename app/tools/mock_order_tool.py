"""
mock_order_tool.py — 订单查询 Mock（Demo Provider）

⚠️ 此文件是 demo/mock 数据提供者，用于 logistics_skill。
仍被 demo 链路使用，不可直接删除。
后续可迁移到真实物流 API 或本地 JSON。
"""


def get_mock_order_info() -> dict:
    """返回 mock 订单和物流信息，用于物流查询。"""
    return {
        "order_id": "ORD-20240101-001",
        "status": "已发货",
        "tracking_no": "SF1234567890",
        "eta": "预计明天到达",
        "items": [{"name": "UPF50+ 轻薄防晒衣", "quantity": 1}],
    }
