"""DeepSeek Provider 测试（Phase 10.13）。使用 mock，不发送真实请求。"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.base import BaseLLMProvider
from app.llm.deepseek_provider import DeepSeekProvider
from app.llm.provider_factory import get_llm_provider
from app.llm.safety import validate_llm_reply


class TestDeepSeekProvider:
    """DeepSeek Provider 测试（全部使用 mock，不调真实 API）。"""

    def test_factory_returns_deepseek(self):
        """LLM_PROVIDER=deepseek 时 factory 返回 DeepSeekProvider。"""
        provider = get_llm_provider("deepseek")
        assert isinstance(provider, DeepSeekProvider)

    def test_default_factory_still_mock(self):
        """默认 factory 仍为 MockLLMProvider。"""
        provider = get_llm_provider()
        from app.llm.mock_provider import MockLLMProvider
        assert isinstance(provider, MockLLMProvider)

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""})
    def test_missing_api_key_fallback(self):
        """没有 API Key 时不崩溃，返回 success=false。"""
        provider = DeepSeekProvider()
        result = provider.generate_reply({"template_reply": "您好"})
        assert result["success"] is False
        assert result["reply"] == "您好"
        assert "missing_api_key" in result.get("error", "")

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"})
    @patch("app.llm.deepseek_provider.httpx.post")
    def test_successful_api_call(self, mock_post):
        """DeepSeek 返回标准 JSON 时能解析 reply。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"reply": "这是润色后的回复。"}'}}]
        }
        mock_post.return_value = mock_response

        provider = DeepSeekProvider()
        result = provider.generate_reply({"template_reply": "原始回复"})
        assert result["success"] is True
        assert result["reply"] == "这是润色后的回复。"

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"})
    @patch("app.llm.deepseek_provider.httpx.post")
    def test_api_error_fallback(self, mock_post):
        """API 报错时 success=false。"""
        mock_post.side_effect = Exception("API error")

        provider = DeepSeekProvider()
        result = provider.generate_reply({"template_reply": "您好"})
        assert result["success"] is False
        assert result["reply"] == "您好"

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"})
    @patch("app.llm.deepseek_provider.httpx.post")
    def test_timeout_fallback(self, mock_post):
        """超时时 success=false。"""
        from httpx import TimeoutException
        mock_post.side_effect = TimeoutException("timeout")

        provider = DeepSeekProvider()
        result = provider.generate_reply({"template_reply": "超时测试"})
        assert result["success"] is False
        assert result["reply"] == "超时测试"
        assert "timeout" in result.get("error", "")

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"})
    @patch("app.llm.deepseek_provider.httpx.post")
    def test_empty_response_fallback(self, mock_post):
        """返回空内容时 success=false。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": ""}}]
        }
        mock_post.return_value = mock_response

        provider = DeepSeekProvider()
        result = provider.generate_reply({"template_reply": "空回复"})
        assert result["success"] is False
        assert result["reply"] == "空回复"

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"})
    def test_dangerous_reply_fallback(self):
        """返回危险承诺时最终会被 safety 拦截。"""
        safety = validate_llm_reply("已经帮您退款成功，请查收。")
        assert safety["safe"] is False

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"})
    @patch("app.llm.deepseek_provider.httpx.post")
    def test_non_json_reply_used(self, mock_post):
        """返回非 JSON 文本时直接作为 reply。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "您好，请问有什么可以帮您？"}}]
        }
        mock_post.return_value = mock_response

        provider = DeepSeekProvider()
        result = provider.generate_reply({"template_reply": "模板回复"})
        assert result["success"] is True
        assert result["reply"] == "您好，请问有什么可以帮您？"
