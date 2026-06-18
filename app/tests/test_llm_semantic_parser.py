"""LLM Semantic Parser 测试（Phase 10.19）。全部 mock，不调真实 API。"""

import os
from unittest.mock import patch

import pytest

from app.graph import run_graph
from app.llm.mock_provider import MockLLMProvider
from app.llm.semantic_parser import (
    ALLOWED_INTENTS,
    ALLOWED_QUERY_TYPES,
    build_parser_payload,
    should_enable,
    validate_semantic_parse,
)
from app.memory.conversation_memory import clear_memory
from app.state.customer_state import create_initial_state


def setup_function():
    clear_memory()


class TestSemanticParserUtils:
    """Semantic Parser 工具函数测试。"""

    def test_should_enable_default_false(self):
        """默认关闭。"""
        assert should_enable() is False

    @patch.dict(os.environ, {"LLM_ENABLE_SEMANTIC_PARSER": "true", "LLM_PROVIDER": "mock"})
    def test_should_enable_true_with_mock(self):
        """mock provider 也可以启用（测试用）。"""
        assert should_enable() is True

    def test_build_parser_payload(self):
        state = {"user_message": "那个遮阳帽不错", "conversation_history": [{"role": "assistant", "content": "推荐了可折叠遮阳帽"}], "intent": "smalltalk", "emotion": "neutral"}
        payload = build_parser_payload(state)
        assert "user_message" in payload
        assert "available_products" in payload
        assert len(payload["available_products"]) >= 3

    def test_allowed_intents(self):
        assert "product_question" in ALLOWED_INTENTS
        assert "refund_request" in ALLOWED_INTENTS
        assert "complaint" in ALLOWED_INTENTS
        assert "human_request" in ALLOWED_INTENTS
        assert "smalltalk" in ALLOWED_INTENTS

    def test_allowed_query_types(self):
        assert "size" in ALLOWED_QUERY_TYPES
        assert "material" in ALLOWED_QUERY_TYPES
        assert "suitability" in ALLOWED_QUERY_TYPES
        assert "policy" in ALLOWED_QUERY_TYPES


class TestValidateSemanticParse:
    """语义解析结果校验测试。"""

    def test_valid_result(self):
        state = {"user_message": "那个遮阳帽不错", "intent": "smalltalk"}
        result = {
            "intent": "product_question", "explicit_product": "可折叠遮阳帽",
            "query_type": "general", "use_history": True,
            "user_signal": "positive_interest", "confidence": 0.85, "reason": "用户表示对遮阳帽感兴趣",
        }
        v = validate_semantic_parse(result, state)
        assert v.get("fallback") is not True

    def test_low_confidence_fallback(self):
        state = {"user_message": "test", "intent": "smalltalk"}
        result = {"intent": "product_question", "confidence": 0.3}
        v = validate_semantic_parse(result, state)
        assert v.get("fallback") is True
        assert "置信度过低" in v.get("reason", "")

    def test_refund_not_downgraded(self):
        """退款词不能被 LLM 降级。"""
        state = {"user_message": "我要退款", "intent": "refund_request"}
        result = {"intent": "smalltalk", "explicit_product": None, "query_type": "unknown", "confidence": 0.9, "use_history": False}
        v = validate_semantic_parse(result, state)
        assert v.get("intent") == "refund_request"

    def test_complaint_not_downgraded(self):
        """投诉词不能被 LLM 降级。"""
        state = {"user_message": "我要投诉", "intent": "complaint"}
        result = {"intent": "smalltalk", "explicit_product": None, "query_type": "unknown", "confidence": 0.9, "use_history": False}
        v = validate_semantic_parse(result, state)
        assert v.get("intent") == "complaint"

    def test_human_request_not_downgraded(self):
        state = {"user_message": "我要找人工", "intent": "human_request"}
        result = {"intent": "smalltalk", "explicit_product": None, "query_type": "unknown", "confidence": 0.9, "use_history": False}
        v = validate_semantic_parse(result, state)
        assert v.get("intent") == "human_request"

    def test_invalid_intent_fallback(self):
        state = {"user_message": "test", "intent": "smalltalk"}
        result = {"intent": "invalid_bogus", "confidence": 0.9}
        v = validate_semantic_parse(result, state)
        assert v.get("fallback") is True

    def test_unknown_product_cleared(self):
        """不存在的商品被清除。"""
        state = {"user_message": "那个怎么样", "intent": "product_question"}
        result = {"intent": "product_question", "explicit_product": "月球车", "query_type": "general", "confidence": 0.85, "use_history": False}
        v = validate_semantic_parse(result, state)
        if v.get("explicit_product") is not None:
            # 如果验证器没有清除，至少不是"月球车"
            assert v["explicit_product"] != "月球车"


class TestMockProvider:
    """Mock Provider parse_semantic 测试。"""

    def test_mock_returns_structured(self):
        provider = MockLLMProvider()
        result = provider.parse_semantic({"user_message": "那个遮阳帽不错"})
        assert result["success"] is True
        assert result["intent"] in ALLOWED_INTENTS
        assert result["confidence"] > 0


class TestDefaultBehavior:
    """关闭 Semantic Parser 时行为不变。"""

    def test_semantic_parser_off(self):
        """LLM_ENABLE_SEMANTIC_PARSER=false 时效果不变。"""
        state = run_graph(create_initial_state(
            session_id="sp-off", user_message="这个衣服是什么材质",
        ))
        assert state["intent"] == "product_question"
        assert state["selected_skill"] == "product_qa_skill"
        assert state["intent_source"] == "rule"

    def test_refund_not_affected(self):
        """退款不受影响。"""
        state = run_graph(create_initial_state(
            session_id="sp-ref", user_message="质量太差了我要退款",
        ))
        assert state["selected_skill"] == "refund_skill"
        assert state["policy_decision"] == "retention"

    def test_state_fields_exist(self):
        """新 state 字段默认值存在。"""
        initial = create_initial_state(session_id="sp-fields", user_message="test")
        assert initial.get("intent_source") == "rule"
        assert initial.get("explicit_product") is None
        assert initial.get("query_type") is None
        assert initial.get("user_signal") is None

    def test_intent_source_in_logs(self):
        """logs 包含 intent_source。"""
        state = run_graph(create_initial_state(
            session_id="sp-log", user_message="这个衣服是什么材质",
        ))
        logs_str = str(state.get("logs", []))
        assert "source=" in logs_str or "intent_source" in logs_str
