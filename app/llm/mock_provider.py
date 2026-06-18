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
