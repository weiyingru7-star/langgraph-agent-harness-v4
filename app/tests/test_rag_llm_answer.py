"""LLM RAG answer 测试（Phase 10.17-C）。全部 mock，不调真实 API。"""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.llm.base import BaseLLMProvider
from app.llm.deepseek_provider import DeepSeekProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.provider_factory import get_llm_provider
from app.llm.safety import validate_rag_answer


class TestMockRagAnswer:
    """Mock Provider RAG answer 测试。"""

    def test_returns_reply_and_sources(self):
        provider = MockLLMProvider()
        result = provider.generate_rag_answer({
            "user_message": "超过7天还能退吗",
            "retrieved_chunks": [
                {"text": "7天无理由退换货", "source_file": "refund_policy.md", "score": 0.9},
            ],
        })
        assert result["success"] is True
        assert "7天" in result["reply"]
        assert "refund_policy.md" in str(result["sources"])

    def test_no_evidence_fallback(self):
        provider = MockLLMProvider()
        result = provider.generate_rag_answer({
            "user_message": "test",
            "retrieved_chunks": [],
        })
        assert result["success"] is False
        assert result["error"] == "no_evidence"


class TestDeepSeekRagAnswer:
    """DeepSeek Provider RAG answer 测试（mock httpx）。"""

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""})
    def test_no_api_key_fallback(self):
        provider = DeepSeekProvider()
        result = provider.generate_rag_answer({
            "user_message": "test",
            "retrieved_chunks": [{"text": "test", "source_file": "test.md", "score": 0.9}],
        })
        assert result["success"] is False
        assert result["error"] == "missing_api_key"

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"})
    def test_no_evidence_returns_error(self):
        provider = DeepSeekProvider()
        result = provider.generate_rag_answer({
            "user_message": "test",
            "retrieved_chunks": [],
        })
        assert result["success"] is False
        assert result["error"] == "no_evidence"

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"})
    @patch("app.llm.deepseek_provider.httpx.post")
    def test_successful_api_call(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"reply": "7天无理由退换货。", "sources": ["refund_policy.md"]}'}}]
        }
        mock_post.return_value = mock_resp

        provider = DeepSeekProvider()
        result = provider.generate_rag_answer({
            "user_message": "超过7天还能退吗",
            "retrieved_chunks": [
                {"text": "7天无理由退换货", "source_file": "refund_policy.md", "score": 0.9},
            ],
        })
        assert result["success"] is True
        assert "7天" in result["reply"]
        assert "refund_policy.md" in result["sources"]


class TestValidateRagAnswer:
    """RAG answer 安全检查测试。"""

    def test_safe_answer(self):
        chunks = [{"text": "7天无理由退换", "source_file": "refund_policy.md", "score": 0.9}]
        result = validate_rag_answer("7天无理由退换货。依据：refund_policy.md", ["refund_policy.md"], chunks)
        assert result["safe"] is True

    def test_empty_reply(self):
        result = validate_rag_answer("", ["test.md"], [{"text": "x", "source_file": "test.md", "score": 0.9}])
        assert result["safe"] is False

    def test_missing_sources(self):
        chunks = [{"text": "x", "source_file": "refund_policy.md", "score": 0.9}]
        result = validate_rag_answer("test reply", [], chunks)
        assert result["safe"] is False
        assert "缺少" in result["reason"]

    def test_source_not_in_chunks(self):
        chunks = [{"text": "x", "source_file": "refund_policy.md", "score": 0.9}]
        result = validate_rag_answer("test reply", ["fake.md"], chunks)
        assert result["safe"] is False
        assert "fake.md" in result["reason"]

    def test_dangerous_refund_promise(self):
        chunks = [{"text": "x", "source_file": "refund_policy.md", "score": 0.9}]
        result = validate_rag_answer("已退款成功，请查收。", ["refund_policy.md"], chunks)
        assert result["safe"] is False

    def test_valid_source_accepted(self):
        chunks = [{"text": "7天无理由退换", "source_file": "care_guide.md", "score": 0.9}]
        result = validate_rag_answer("防晒衣建议冷水洗。依据：care_guide.md", ["care_guide.md"], chunks)
        assert result["safe"] is True


class TestKnowledgeQASkillRAGAnswer:
    """knowledge_qa_skill 的 LLM RAG answer 集成测试。"""

    def test_rag_answer_off_uses_template(self):
        """LLM_ENABLE_RAG_ANSWER=false 时用模板回复。"""
        from app.graph import run_graph
        from app.state.customer_state import create_initial_state

        state = run_graph(create_initial_state(
            session_id="rag-off", user_message="超过7天还能退吗",
        ))
        sr = state.get("skill_result", {}) or {}
        # 未开启 RAG answer 时 source = "rag"（不是 rag_llm）
        assert sr.get("source") in ("rag",)
        assert "refund_policy" in state["reply"] or "来源" in state["reply"]

    def test_refund_still_policy(self):
        """退款不走 RAG answer。"""
        from app.graph import run_graph
        from app.state.customer_state import create_initial_state

        state = run_graph(create_initial_state(
            session_id="rag-ref", user_message="我要退款",
        ))
        assert state["selected_skill"] == "refund_skill"

    def test_product_size_still_structured(self):
        """尺码不走 RAG。"""
        from app.graph import run_graph
        from app.state.customer_state import create_initial_state

        state = run_graph(create_initial_state(
            session_id="rag-size", user_message="运动外套有什么尺码",
        ))
        assert state["selected_skill"] == "product_qa_skill"
