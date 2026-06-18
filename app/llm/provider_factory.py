"""
provider_factory.py — 根据环境变量选择 LLM Provider。

默认返回 MockLLMProvider，不调用真实 API。
"""

import os

from app.llm.base import BaseLLMProvider
from app.llm.mock_provider import MockLLMProvider

_PROVIDERS: dict[str, type[BaseLLMProvider]] = {
    "mock": MockLLMProvider,
}


def get_llm_provider(provider_name: str | None = None) -> BaseLLMProvider:
    """
    根据环境变量 LLM_PROVIDER 选择 Provider。

    Args:
        provider_name: 可选，覆盖环境变量

    Returns:
        对应 Provider 实例（默认 MockLLMProvider）
    """
    name = provider_name or os.getenv("LLM_PROVIDER", "mock")
    cls = _PROVIDERS.get(name)
    if cls is None:
        return MockLLMProvider()
    return cls()
