"""
base.py — LLM Provider 统一接口。

所有 LLM Provider 必须继承 BaseLLMProvider 并实现 generate_reply。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseLLMProvider(ABC):
    """LLM Provider 统一接口。"""

    @abstractmethod
    def generate_reply(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成或润色回复。

        Args:
            payload: 包含 user_message, intent, emotion, skill_result,
                     policy_decision, conversation_history, template_reply 等

        Returns:
            {"reply": str, "provider": str, "success": bool}
            或 {"error": str}
        """

    def generate_rag_answer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于 RAG retrieved_chunks 生成回答。

        Args:
            payload: 包含 user_message, conversation_history,
                     retrieved_chunks, safety_rules 等

        Returns:
            {"reply": str, "sources": list, "provider": str, "success": bool}
            或 {"error": str}
        """
        raise NotImplementedError("generate_rag_answer not implemented")

    def parse_semantic(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        语义解析。

        Args:
            payload: 包含 user_message, conversation_history,
                     available_products, safety_rules 等

        Returns:
            {"intent": str, "explicit_product": str|null, "query_type": str,
             "use_history": bool, "confidence": float,
             "provider": str, "success": bool}
            或 {"error": str}
        """
        raise NotImplementedError("parse_semantic not implemented")
