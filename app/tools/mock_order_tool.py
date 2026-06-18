"""
mock_order_tool.py — Mock 订单查询工具

职责: 模拟查询外部电商系统的订单数据。
      第一版不接真实 API，返回 mock 数据。
"""


def query_order(order_id: str) -> dict:
    """
    模拟查询订单信息。

    Args:
        order_id: 订单号

    Returns:
        模拟的订单数据
    """
    # TODO: 后续阶段丰富 mock 数据
    return {
        "order_id": order_id,
        "status": "shipped",
        "amount": 100.0,
        "message": "订单查询成功（mock 数据）",
    }
