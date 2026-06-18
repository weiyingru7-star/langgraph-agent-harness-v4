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
