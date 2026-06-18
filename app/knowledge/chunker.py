"""
chunker.py — 文档切片工具。

将长文本文档按段落或固定大小切分为 chunks，
保留 source_file 引用。
"""

import hashlib
from typing import Any, Dict, List


def chunk_documents(documents: List[Dict[str, Any]], chunk_size: int = 512) -> List[Dict[str, Any]]:
    """
    将文档列表切分为 chunks。

    策略：按段落（双换行）分割，段落过长时再按句子分割。
    每个 chunk 保留 source_file。

    Args:
        documents: [{"source_file": str, "text": str, "metadata": dict}]
        chunk_size: 每 chunk 最大字符数

    Returns:
        [{"chunk_id": str, "text": str, "source_file": str, "metadata": dict}]
    """
    chunks = []

    for doc in documents:
        source_file = doc["source_file"]
        text = doc["text"]
        base_meta = doc.get("metadata", {})

        # 按段落分割
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        for para in paragraphs:
            if len(para) <= chunk_size:
                chunk_id = hashlib.md5(para.encode()).hexdigest()[:12]
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": para,
                    "source_file": source_file,
                    "metadata": {**base_meta, "start_char": text.find(para)},
                })
            else:
                # 段落过长：按句号分割
                sentences = []
                current = ""
                for char in para:
                    current += char
                    if char in ("。", "！", "？", "\n"):
                        if current.strip():
                            sentences.append(current.strip())
                            current = ""
                if current.strip():
                    sentences.append(current.strip())

                for sent in sentences:
                    if not sent:
                        continue
                    chunk_id = hashlib.md5(sent.encode()).hexdigest()[:12]
                    chunks.append({
                        "chunk_id": chunk_id,
                        "text": sent,
                        "source_file": source_file,
                        "metadata": {**base_meta, "start_char": text.find(sent)},
                    })

    return chunks
