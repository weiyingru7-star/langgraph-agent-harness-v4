"""
local_product_tool.py — 本地商品知识库查询工具。

从 data/products.json 读取商品资料，通过名称/别名匹配查询。
第一版不做 embedding，后续可升级为 Dify / RAG。
"""

import json
import os
from typing import Any, Dict, List, Optional

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_PRODUCTS_PATH = os.path.normpath(os.path.join(_DATA_DIR, "products.json"))


def _load_products() -> list[dict]:
    """加载 products.json，文件不存在或异常时返回空列表。"""
    try:
        with open(_PRODUCTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, Exception):
        return []


def resolve_product(text: str) -> Dict[str, Any]:
    """
    通用商品解析器：从 products.json 动态匹配商品。

    匹配顺序（只在当前输入中搜索）：
        1. 完全命中 name
        2. 完全命中 aliases
        3. 完全命中 category

    不匹配 features / scene，避免误匹配。
    不依赖代码硬编码商品名。

    Returns:
        {"matched": True, "matched_product": dict}  |  {"matched": False, ...}
    """
    products = _load_products()
    if not products:
        return {"matched": False, "matched_product": None, "reason": "data_unavailable"}

    for product in products:
        # 1. name 完全在输入中
        if product["name"] in text:
            return {"matched": True, "matched_product": product}

        # 2. aliases
        for alias in product.get("aliases", []):
            if alias in text:
                return {"matched": True, "matched_product": product}

        # 3. category
        if product.get("category", "") in text:
            return {"matched": True, "matched_product": product}

    return {"matched": False, "matched_product": None, "reason": "no_match"}


def find_product_in_history(history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    从对话历史中查找最近提到的商品。

    遍历 assistant 回复（从最新到最旧），匹配 name / aliases。

    Returns:
        同上 resolve_product 结构。
    """
    products = _load_products()
    if not products:
        return {"matched": False, "matched_product": None, "reason": "data_unavailable"}

    for msg in reversed(history):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        if not content:
            continue
        for product in products:
            if product["name"] in content:
                return {"matched": True, "matched_product": product}
            for alias in product.get("aliases", []):
                if alias in content:
                    return {"matched": True, "matched_product": product}
    return {"matched": False, "matched_product": None, "reason": "no_match"}


def get_all_products() -> List[dict]:
    """返回所有商品列表。"""
    return _load_products()


# ══════════════════════════════════════════════
#  保留向后兼容
# ══════════════════════════════════════════════

def query_product(text: str) -> Dict[str, Any]:
    """
    旧版接口：关键词 + name + category + features 匹配。
    保留供 query_product 调用方使用。
    """
    products = _load_products()
    if not products:
        return {"matched": False, "knowledge_source": "local_json", "matched_product": None, "reason": "data_unavailable"}

    for product in products:
        for alias in product.get("aliases", []):
            if alias in text:
                return {"matched": True, "knowledge_source": "local_json", "matched_product": product}
        if product["name"] in text or product.get("category", "") in text:
            return {"matched": True, "knowledge_source": "local_json", "matched_product": product}
        for kw in product.get("keywords", []):
            if kw in text:
                return {"matched": True, "knowledge_source": "local_json", "matched_product": product}

    return {
        "matched": False,
        "knowledge_source": "local_json",
        "matched_product": None,
        "products": products[:2],
        "reason": "no_match",
    }


def find_product_by_name(text: str) -> dict:
    """旧版接口：alias / name / category 匹配。"""
    return resolve_product(text)
