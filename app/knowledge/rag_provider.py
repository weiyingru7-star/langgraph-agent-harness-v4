"""
rag_provider.py — RAG 检索 Provider。

封装文档加载 → 切片 → 索引 → 检索的完整链路。
第一版不接入 Agent 主流程，仅提供检索能力。
"""

import os
from typing import Any, Dict, List

from app.knowledge.chunker import chunk_documents
from app.knowledge.document_loader import load_documents
from app.knowledge.vector_store import SimpleVectorStore

_INDEX_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "knowledge", "index"))
_INDEX_PATH = os.path.join(_INDEX_DIR, "vector_store.json")


class RagProvider:
    """本地 RAG 检索 Provider。"""

    def __init__(self):
        self.store = SimpleVectorStore()
        self._built = False

    def build_index(self) -> dict:
        """加载文档 → 切片 → 构建索引。"""
        docs = load_documents()
        if not docs:
            return {"status": "error", "reason": "no_documents", "chunk_count": 0}

        chunks = chunk_documents(docs)
        self.store.build(chunks)
        self._built = True

        # 保存到文件
        try:
            self.store.save(_INDEX_PATH)
        except Exception as e:
            print(f"[rag_provider] 保存索引失败: {e}")

        return {
            "status": "ok",
            "document_count": len(docs),
            "chunk_count": len(chunks),
        }

    def load_index(self) -> bool:
        """从文件加载已有索引。"""
        if os.path.exists(_INDEX_PATH):
            try:
                self.store.load(_INDEX_PATH)
                self._built = True
                return True
            except Exception as e:
                print(f"[rag_provider] 加载索引失败: {e}")
        return False

    def retrieve(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """
        检索与 query 相关的 chunks。

        Args:
            query: 用户查询文本
            top_k: 返回 top_k 条结果

        Returns:
            {
                "source": "rag",
                "matched": bool,
                "query": str,
                "retrieved_chunks": [...],
                "needs_clarification": bool,
                "reason": str
            }
        """
        if not self._built:
            # 尝试加载
            loaded = self.load_index()
            if not loaded:
                # 自动构建
                result = self.build_index()
                if result.get("status") != "ok":
                    return {
                        "source": "rag",
                        "matched": False,
                        "query": query,
                        "retrieved_chunks": [],
                        "needs_clarification": True,
                        "reason": "index_not_available",
                    }

        chunks = self.store.search(query, top_k=top_k)

        if not chunks:
            return {
                "source": "rag",
                "matched": False,
                "query": query,
                "retrieved_chunks": [],
                "needs_clarification": True,
                "reason": "no_relevant_chunks",
            }

        # 阈值过滤：低于 0.05 视为不相关
        relevant = [c for c in chunks if c["score"] >= 0.05]

        if not relevant:
            return {
                "source": "rag",
                "matched": False,
                "query": query,
                "retrieved_chunks": [],
                "needs_clarification": True,
                "reason": "low_relevance",
            }

        return {
            "source": "rag",
            "matched": True,
            "query": query,
            "retrieved_chunks": relevant,
            "needs_clarification": False,
            "reason": "",
        }
