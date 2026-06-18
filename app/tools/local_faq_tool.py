"""
local_faq_tool.py — 本地 FAQ 知识库查询工具。

从 data/faq.json 读取常见问答，通过关键词 + intent 匹配。
第一版不做 embedding，后续可升级为 Dify / RAG。
"""

import json
import os
from typing import Any, Dict, Optional

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_FAQ_PATH = os.path.normpath(os.path.join(_DATA_DIR, "faq.json"))


def _load_faqs() -> list[dict]:
    """加载 faq.json，文件不存在或异常时返回空列表。"""
    try:
        with open(_FAQ_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, Exception):
        return []


def query_faq(text: str, intent: Optional[str] = None) -> Dict[str, Any]:
    """
    根据用户输入文本和 intent 匹配 FAQ。

    匹配策略：
        1. 优先匹配 intent + keywords
        2. 其次只匹配 keywords

    Args:
        text: 用户输入文本
        intent: 当前识别的 intent（可选）

    Returns:
        dict: {
            "matched": bool,
            "knowledge_source": "local_json",
            "matched_faq": dict | None
        }
    """
    faqs = _load_faqs()
    if not faqs:
        return {"matched": False, "knowledge_source": "local_json", "matched_faq": None, "reason": "data_unavailable"}

    text_lower = text.lower()
    matched = []

    for faq in faqs:
        for kw in faq.get("question_keywords", []):
            if kw in text:
                # intent 匹配优先
                if intent and intent in faq.get("related_intents", []):
                    return {"matched": True, "knowledge_source": "local_json", "matched_faq": faq}
                matched.append(faq)
                break

    # 没有 intent 匹配，返回第一个关键词匹配的
    if matched:
        return {"matched": True, "knowledge_source": "local_json", "matched_faq": matched[0]}

    return {"matched": False, "knowledge_source": "local_json", "matched_faq": None, "reason": "no_match"}
