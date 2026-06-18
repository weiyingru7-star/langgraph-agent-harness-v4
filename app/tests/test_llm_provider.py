"""LLM Provider 测试（Phase 10.12）。"""

import os
from unittest.mock import patch

from app.llm.base import BaseLLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.provider_factory import get_llm_provider
from app.llm.safety import validate_llm_reply


class TestProviderFactory:
    """Provider 工厂测试。"""

    def test_default_is_mock(self):
        provider = get_llm_provider()
        assert isinstance(provider, MockLLMProvider)

    def test_unknown_fallback_to_mock(self):
        provider = get_llm_provider("unknown_provider")
        assert isinstance(provider, MockLLMProvider)

    def test_explicit_mock(self):
        provider = get_llm_provider("mock")
        assert isinstance(provider, MockLLMProvider)


class TestMockProvider:
    """Mock Provider 功能测试。"""

    def test_returns_reply(self):
        provider = MockLLMProvider()
        result = provider.generate_reply({"template_reply": "您好"})
        assert result["reply"] == "您好"
        assert result["success"] is True
        assert result["provider"] == "mock"

    def test_empty_template_reply(self):
        provider = MockLLMProvider()
        result = provider.generate_reply({})
        assert result["reply"] == ""


class TestSafety:
    """安全检查测试。"""

    def test_safe_reply(self):
        result = validate_llm_reply("您好，这款防晒衣透气性很好。")
        assert result["safe"] is True

    def test_detect_refund_promise(self):
        result = validate_llm_reply("已退款成功，请查收。")
        assert result["safe"] is False
        assert "已退款成功" in result["blocked_terms"]

    def test_refund_completed(self):
        result = validate_llm_reply("已经帮您退款，请查收。")
        assert result["safe"] is False

    def test_detect_refund_phrase(self):
        result = validate_llm_reply("我已经帮您退款了")
        assert result["safe"] is False

    def test_detect_compensation(self):
        result = validate_llm_reply("已补发商品，请您注意查收。")
        assert result["safe"] is False

    def test_detect_order_cancelled(self):
        result = validate_llm_reply("已取消订单，退款将在3个工作日内到账。")
        assert result["safe"] is False

    def test_need_human_missing_keywords(self):
        """need_human=True 时回复必须提及人工/客服/专员。"""
        result = validate_llm_reply(
            "好的我明白了",
            state={"need_human": True},
        )
        assert result["safe"] is False
        assert "need_human" in result["reason"]

    def test_need_human_with_keyword(self):
        result = validate_llm_reply(
            "正在为您转接人工客服",
            state={"need_human": True},
        )
        assert result["safe"] is True

    def test_need_human_false_no_check(self):
        """need_human=False 时不强制检查人工关键词。"""
        result = validate_llm_reply(
            "好的我明白了",
            state={"need_human": False},
        )
        assert result["safe"] is True


class TestGenerateReplyWithLLM:
    """generate_reply 在 LLM 开关下的行为测试。"""

    def test_llm_off_by_default(self):
        """LLM_ENABLE_REPLY_POLISH=false 时行为和原来一致。"""
        from app.nodes.generate_reply import generate_reply
        from app.state.customer_state import create_initial_state
        from app.graph import run_graph

        state = run_graph(create_initial_state(
            session_id="llm-off", user_message="这个衣服是什么材质",
        ))
        assert state["reply"] is not None
        # 不应包含 LLM 相关的日志标记
        logs_str = str(state.get("logs", []))
        assert "llm_used" not in logs_str

    def test_llm_on_does_not_modify_policy(self):
        """LLM 开启时不应修改 policy_decision 等业务字段。"""
        from app.graph import run_graph
        from app.state.customer_state import create_initial_state

        state = run_graph(create_initial_state(
            session_id="llm-policy", user_message="质量太差了我要退款",
        ))
        # policy 应该仍然是 retention
        assert state["policy_decision"] == "retention"
        assert state["selected_skill"] == "refund_skill"
