"""
provider_factory.py — RAG Provider 工厂。

根据环境变量 RAG_PROVIDER 选择检索后端。
    tfidf  → 当前 TF-IDF RAG（默认）
    chroma → Chroma 向量检索

默认 tfidf，零外部依赖。
Chroma 初始化失败时自动 fallback 到 tfidf。
"""

import os
from typing import Any, Dict

from app.knowledge.chroma_provider import ChromaProvider
from app.knowledge.rag_provider import RagProvider


def get_rag_provider() -> Any:
    """
    根据 RAG_PROVIDER 环境变量选择 Provider。

    Returns:
        RagProvider 或 ChromaProvider 实例
    """
    provider_name = os.getenv("RAG_PROVIDER", "tfidf")

    if provider_name == "chroma":
        try:
            import chromadb  # noqa: F401 — 仅检查是否可导入
            return ChromaProvider()
        except ImportError as e:
            print(f"[provider_factory] chromadb 不可用: {e}，fallback 到 tfidf")
        except Exception as e:
            print(f"[provider_factory] Chroma 初始化异常: {e}，fallback 到 tfidf")

    return RagProvider()


def get_provider_name() -> str:
    """获取当前使用的 provider 名称。"""
    return os.getenv("RAG_PROVIDER", "tfidf")
