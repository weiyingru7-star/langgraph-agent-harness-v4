"""
chroma_provider.py — Chroma Vector RAG Provider。

使用 ChromaDB + sentence-transformers 做向量检索。
支持持久化到本地目录。初始化失败时提供 fallback 信号。
"""

import os
import sys
from typing import Any, Dict, List

from app.knowledge.chunker import chunk_documents
from app.knowledge.document_loader import load_documents

_CHROMA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "chroma"))
_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")


class ChromaProvider:
    """Chroma 向量 RAG Provider。"""

    def __init__(self):
        self._collection = None
        self._client = None
        self._built = False
        self._error = None
        self._load_existing()

    def _load_existing(self):
        """尝试加载已有索引，不重建。"""
        try:
            import chromadb
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

            if not os.path.isdir(_CHROMA_DIR):
                return

            embed_func = SentenceTransformerEmbeddingFunction(model_name=_EMBEDDING_MODEL)
            client = chromadb.PersistentClient(path=_CHROMA_DIR)
            collection = client.get_collection(
                name="knowledge_chunks",
                embedding_function=embed_func,
            )
            # 验证 collection 非空
            count = collection.count()
            if count > 0:
                self._client = client
                self._collection = collection
                self._built = True
        except Exception:
            pass

    def build_index(self) -> dict:
        """加载文档 → 切片 → 构建 Chroma 索引。"""
        try:
            import chromadb
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

            docs = load_documents()
            if not docs:
                return {"status": "error", "reason": "no_documents", "chunk_count": 0}

            chunks = chunk_documents(docs)
            if not chunks:
                return {"status": "error", "reason": "no_chunks", "chunk_count": 0}

            # 初始化 embedding 函数
            try:
                embed_func = SentenceTransformerEmbeddingFunction(model_name=_EMBEDDING_MODEL)
            except Exception as e:
                print(f"[chroma_provider] 加载 embedding 模型失败: {e}")
                return {"status": "error", "reason": f"embedding_model_failed: {e}", "chunk_count": 0}

            # 初始化 Chroma 客户端
            os.makedirs(_CHROMA_DIR, exist_ok=True)
            client = chromadb.PersistentClient(path=_CHROMA_DIR)

            # 删除已有 collection 并重建
            try:
                client.delete_collection("knowledge_chunks")
            except Exception:
                pass

            collection = client.create_collection(
                name="knowledge_chunks",
                embedding_function=embed_func,
                metadata={"hnsw:space": "cosine"},
            )

            # 准备数据
            ids = [c["chunk_id"] for c in chunks]
            texts = [c["text"] for c in chunks]
            metadatas = [{"source_file": c["source_file"]} for c in chunks]

            # 分批添加（避免大 batch 问题）
            batch_size = 50
            for i in range(0, len(ids), batch_size):
                end = i + batch_size
                collection.add(
                    ids=ids[i:end],
                    documents=texts[i:end],
                    metadatas=metadatas[i:end],
                )

            self._client = client
            self._collection = collection
            self._built = True
            self._error = None

            return {
                "status": "ok",
                "document_count": len(docs),
                "chunk_count": len(chunks),
                "embedding_model": _EMBEDDING_MODEL,
                "persist_dir": _CHROMA_DIR,
            }

        except ImportError as e:
            msg = f"chromadb 未安装: {e}"
            print(f"[chroma_provider] {msg}")
            self._error = msg
            return {"status": "error", "reason": "chromadb_not_installed", "chunk_count": 0}
        except Exception as e:
            msg = f"构建 Chroma 索引失败: {e}"
            print(f"[chroma_provider] {msg}")
            self._error = msg
            return {"status": "error", "reason": str(e), "chunk_count": 0}

    def retrieve(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """
        检索与 query 相关的 chunks。

        Returns:
            和 TF-IDF retrieve 兼容的结构。
        """
        if not self._built:
            result = self.build_index()
            if result.get("status") != "ok":
                return {
                    "source": "rag",
                    "provider": "chroma",
                    "matched": False,
                    "query": query,
                    "retrieved_chunks": [],
                    "needs_clarification": True,
                    "reason": self._error or "index_not_available",
                }

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
            )

            if not results or not results.get("documents") or not results["documents"][0]:
                return {
                    "source": "rag",
                    "provider": "chroma",
                    "matched": False,
                    "query": query,
                    "retrieved_chunks": [],
                    "needs_clarification": True,
                    "reason": "no_relevant_chunks",
                }

            chunks = []
            for i in range(len(results["documents"][0])):
                text = results["documents"][0][i]
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 1.0
                # 将 cosine distance 转换为 similarity score (1 - distance)
                score = max(0.0, 1.0 - distance)

                chunks.append({
                    "text": text,
                    "source_file": meta.get("source_file", "unknown"),
                    "score": round(score, 4),
                })

            # 阈值过滤
            relevant = [c for c in chunks if c["score"] >= 0.3]
            if not relevant:
                return {
                    "source": "rag",
                    "provider": "chroma",
                    "matched": False,
                    "query": query,
                    "retrieved_chunks": [],
                    "needs_clarification": True,
                    "reason": "low_relevance",
                }

            return {
                "source": "rag",
                "provider": "chroma",
                "matched": True,
                "query": query,
                "retrieved_chunks": relevant,
                "needs_clarification": False,
                "reason": "",
            }

        except Exception as e:
            print(f"[chroma_provider] 检索失败: {e}")
            return {
                "source": "rag",
                "provider": "chroma",
                "matched": False,
                "query": query,
                "retrieved_chunks": [],
                "needs_clarification": True,
                "reason": str(e),
            }
