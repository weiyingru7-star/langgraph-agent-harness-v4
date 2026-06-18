"""
vector_store.py — 简易向量存储。

使用 TF-IDF + 余弦相似度，纯 Python 标准库实现。
不需要外部依赖。
"""

import json
import math
import os
from collections import Counter
from typing import Any, Dict, List, Tuple


def _tokenize(text: str) -> List[str]:
    """简单中文分词：按字符 bigram + 常用词分割。"""
    import re
    # 按非汉字/数字分割
    tokens = re.findall(r'[\w]+', text.lower())
    result = []
    for token in tokens:
        if len(token) <= 1:
            continue
        result.append(token)
        # 对中文词加 bigram
        if any('一' <= c <= '鿿' for c in token) and len(token) >= 2:
            for i in range(len(token) - 1):
                result.append(token[i:i+2])
    return result


def _tfidf_vectorize(text: str, idf: Dict[str, float]) -> Dict[str, float]:
    """将文本转为 TF-IDF 向量（dict 稀疏表示）。"""
    tokens = _tokenize(text)
    if not tokens:
        return {}
    tf = Counter(tokens)
    max_tf = max(tf.values())
    vec = {}
    for word, count in tf.items():
        tf_val = count / max_tf
        idf_val = idf.get(word, 1.0)
        vec[word] = tf_val * idf_val
    return vec


def _cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    """计算两个稀疏向量的余弦相似度。"""
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for word, val in a.items():
        norm_a += val * val
        if word in b:
            dot += val * b[word]
    for val in b.values():
        norm_b += val * val
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


class SimpleVectorStore:
    """简易向量存储：TF-IDF + 余弦相似度。"""

    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.idf: Dict[str, float] = {}
        self.vectors: List[Dict[str, float]] = []

    def build(self, chunks: List[Dict[str, Any]]) -> None:
        """从 chunks 构建索引。"""
        self.chunks = chunks

        # 计算 IDF
        n_docs = len(chunks)
        df: Counter = Counter()
        for chunk in chunks:
            tokens = set(_tokenize(chunk["text"]))
            for token in tokens:
                df[token] += 1

        self.idf = {}
        for word, count in df.items():
            self.idf[word] = math.log((n_docs + 1) / (count + 1)) + 1

        # 计算 TF-IDF 向量
        self.vectors = []
        for chunk in chunks:
            self.vectors.append(_tfidf_vectorize(chunk["text"], self.idf))

    def save(self, path: str) -> None:
        """保存索引到 JSON 文件。"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "chunks": self.chunks,
            "idf": {k: v for k, v in sorted(self.idf.items())},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> None:
        """从 JSON 文件加载索引。"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.chunks = data["chunks"]
        self.idf = data["idf"]
        # 重建向量
        self.vectors = []
        for chunk in self.chunks:
            self.vectors.append(_tfidf_vectorize(chunk["text"], self.idf))

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        检索与 query 最相似的 chunks。

        Returns:
            [{"text": str, "source_file": str, "score": float, "metadata": dict}, ...]
        """
        if not self.chunks:
            return []

        query_vec = _tfidf_vectorize(query, self.idf)
        scored = []

        for i, chunk in enumerate(self.chunks):
            score = _cosine_similarity(query_vec, self.vectors[i])
            if score > 0:
                scored.append({
                    "text": chunk["text"],
                    "source_file": chunk["source_file"],
                    "score": round(score, 4),
                    "metadata": chunk.get("metadata", {}),
                })

        # 按分数降序排列
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
