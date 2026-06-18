"""
local_product_tool.py — 本地商品知识库查询工具。

从 data/products.json 读取商品资料，通过关键词匹配查询。
第一版不做 embedding，后续可升级为 Dify / RAG。
"""

import json
import os
from typing import Any, Dict, Optional

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_PRODUCTS_PATH = os.path.normpath(os.path.join(_DATA_DIR, "products.json"))


def _load_products() -> list[dict]:
    """加载 products.json，文件不存在或异常时返回空列表。"""
    try:
        with open(_PRODUCTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, Exception):
        return []


def query_product(text: str) -> Dict[str, Any]:
    """
    根据用户输入文本匹配商品。

    匹配策略（优先顺序）：
        1. keywords 关键词命中
        2. name / category 包含
        3. features / suitable_scene 包含

    Args:
        text: 用户输入文本

    Returns:
        dict: {
            "matched": bool,
            "knowledge_source": "local_json",
            "matched_product": dict | None,
            "products": list[dict]  # 未精确匹配时返回前 2 个
        }
    """
    products = _load_products()
    if not products:
        return {"matched": False, "knowledge_source": "local_json", "matched_product": None, "reason": "data_unavailable"}

    text_lower = text.lower()

    # 1. 关键词精确匹配
    for product in products:
        for kw in product.get("keywords", []):
            if kw in text:
                return {"matched": True, "knowledge_source": "local_json", "matched_product": product}

    # 2. name / category 包含
    for product in products:
        if product["name"] in text or product.get("category", "") in text:
            return {"matched": True, "knowledge_source": "local_json", "matched_product": product}

    # 3. features / scene 包含
    for product in products:
        for feat in product.get("features", []):
            if feat in text:
                return {"matched": True, "knowledge_source": "local_json", "matched_product": product}
        for scene in product.get("suitable_scene", []):
            if scene in text:
                return {"matched": True, "knowledge_source": "local_json", "matched_product": product}

    # 未命中：返回前 2 个供参考
    return {
        "matched": False,
        "knowledge_source": "local_json",
        "matched_product": None,
        "products": products[:2],
        "reason": "no_match",
    }
