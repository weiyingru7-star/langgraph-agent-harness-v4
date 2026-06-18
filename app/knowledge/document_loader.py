"""
document_loader.py — 本地文档加载器。

读取 knowledge/raw 下的 Markdown/TXT 文件，
返回结构化文档列表。
"""

import os
from typing import Any, Dict, List

_RAW_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "knowledge", "raw"))


def load_documents() -> List[Dict[str, Any]]:
    """
    加载 knowledge/raw 下的所有文档。

    Returns:
        [{"source_file": str, "text": str, "metadata": dict}, ...]
    """
    documents = []
    if not os.path.isdir(_RAW_DIR):
        return documents

    for filename in sorted(os.listdir(_RAW_DIR)):
        if not filename.endswith((".md", ".txt")):
            continue
        filepath = os.path.join(_RAW_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read().strip()
            if text:
                documents.append({
                    "source_file": filename,
                    "text": text,
                    "metadata": {"filepath": filepath},
                })
        except (IOError, OSError) as e:
            print(f"[document_loader] 读取失败 {filename}: {e}")

    return documents
