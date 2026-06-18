"""
mock_product_tool.py — 商品查询 Mock

职责：模拟查询商品信息。第一版不接真实 API。
      Tool 只负责提供外部数据，不负责业务决策。
"""


def get_mock_product_info() -> dict:
    """返回 mock 商品信息，用于商品问答和推荐。"""
    return {
        "product_name": "经典款运动鞋",
        "material": "透气网面 + EVA 鞋底",
        "size": "39-44码可选",
        "features": ["轻便", "防滑", "透气"],
        "suitable_scene": "日常跑步、健身、休闲穿着",
    }
