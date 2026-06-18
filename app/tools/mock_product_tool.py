"""
mock_product_tool.py — 商品查询 Mock（Legacy）

⚠️ 此文件是 legacy mock，仅用于 product_qa_skill / recommendation_skill 的回退兜底。
主要商品数据来源已迁移到 data/products.json（local_product_tool）。
新功能请使用 local_product_tool，不要扩展此文件。
"""


def get_mock_product_info() -> dict:
    """返回 mock 商品信息，用于商品问答和推荐。

    当前使用服饰类 mock 数据，与电商客服 Demo 场景一致。
    后续接入 data/products.json 本地知识库后替换此函数。
    """
    return {
        "product_name": "UPF50+ 轻薄防晒衣",
        "material": "锦纶混纺 + 透气网眼",
        "size": "M/L/XL 可选",
        "features": ["轻薄", "透气", "UPF50+防晒", "防泼水"],
        "suitable_scene": "夏季通勤、骑行、户外活动、日常防晒",
    }
