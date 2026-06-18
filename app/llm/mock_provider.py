"""
mock_provider.py — Mock LLM Provider。

不调用任何真实 API，返回 template_reply 原文。
用于测试和默认场景。
"""

from app.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Mock Provider：不调用真实 API，返回 template_reply。"""

    def generate_reply(self, payload: dict) -> dict:
        """返回 template_reply，不做任何润色。"""
        reply = payload.get("template_reply", "")
        return {
            "reply": reply,
            "provider": "mock",
            "success": True,
        }

    def generate_rag_answer(self, payload: dict) -> dict:
        """Mock RAG answer：基于 retrieved_chunks 返回文本。"""
        chunks = payload.get("retrieved_chunks", [])
        if not chunks:
            return {"reply": "", "sources": [], "provider": "mock", "success": False, "error": "no_evidence"}
        texts = [c["text"] for c in chunks]
        sources = list(set(c["source_file"] for c in chunks))
        return {
            "reply": "\n".join(texts[:2]) + f"\n（依据：{'、'.join(sources)}）",
            "sources": sources,
            "provider": "mock",
            "success": True,
        }

    def parse_semantic(self, payload: dict) -> dict:
        """Mock 语义解析。"""
        text = payload.get("user_message", "") or ""
        if not text:
            return {"intent": "smalltalk", "explicit_product": None, "query_type": "unknown",
                    "use_history": False, "confidence": 0.3, "provider": "mock", "success": True}
        return {"intent": "product_question", "explicit_product": None, "query_type": "general",
                "use_history": False, "confidence": 0.7, "provider": "mock", "success": True}
