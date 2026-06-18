"""
mock_product_tool.py — Mock 商品查询工具

职责: 模拟查询商品信息。
      第一版不接真实 API，返回 mock 数据。
"""


def query_product(product_id: str) -> dict:
    """
    模拟查询商品信息。

    Args:
        product_id: 商品 ID

    Returns:
        模拟的商品数据
    """
    # TODO: 后续阶段丰富 mock 数据
    return {
        "product_id": product_id,
        "name": "示例商品",
        "price": 99.9,
        "stock": 100,
        "message": "商品查询成功（mock 数据）",
    }
