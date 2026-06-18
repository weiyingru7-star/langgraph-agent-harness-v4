"""Chroma RAG Provider 测试（Phase 11.2）。"""

import os
from unittest.mock import patch

import pytest

from app.knowledge.chroma_provider import ChromaProvider
from app.knowledge.provider_factory import get_provider_name, get_rag_provider
from app.knowledge.rag_provider import RagProvider


class TestProviderFactory:
    """Provider Factory 测试。"""

    def test_default_is_tfidf(self):
        """RAG_PROVIDER 默认 tfidf。"""
        provider = get_rag_provider()
        assert isinstance(provider, RagProvider)

    @patch.dict(os.environ, {"RAG_PROVIDER": "tfidf"})
    def test_explicit_tfidf(self):
        provider = get_rag_provider()
        assert isinstance(provider, RagProvider)

    @patch.dict(os.environ, {"RAG_PROVIDER": "chroma"})
    def test_chroma_selected(self):
        """RAG_PROVIDER=chroma 时返回 ChromaProvider。"""
        provider = get_rag_provider()
        from app.knowledge.chroma_provider import ChromaProvider as CP
        assert isinstance(provider, CP)

    @patch.dict(os.environ, {"RAG_PROVIDER": "unknown"})
    def test_unknown_provider_fallback_to_tfidf(self):
        """未知 provider fallback 到 TF-IDF。"""
        provider = get_rag_provider()
        assert isinstance(provider, RagProvider)


class TestTfidfFallback:
    """TF-IDF fallback 行为测试。"""

    def test_tfidf_still_works(self):
        """默认 TF-IDF 检索正常。"""
        from app.graph import run_graph
        from app.state.customer_state import create_initial_state

        state = run_graph(create_initial_state(
            session_id="rag-tfidf", user_message="超过7天还能退吗",
        ))
        assert state["selected_skill"] == "knowledge_qa_skill"
        sr = state.get("skill_result", {}) or {}
        assert sr.get("rag_provider", "") in ("", "tfidf")
        assert len(sr.get("evidence", [])) > 0


class TestKnowledgeQASkill:
    """knowledge_qa_skill RAG provider 记录测试。"""

    def test_rag_provider_in_skill_result(self):
        """skill_result 包含 rag_provider 字段。"""
        from app.graph import run_graph
        from app.state.customer_state import create_initial_state

        state = run_graph(create_initial_state(
            session_id="rag-kb", user_message="超过7天还能退吗",
        ))
        sr = state.get("skill_result", {}) or {}
        assert "rag_provider" in sr

    def test_care_guide_retrievable(self):
        """防晒衣怎么洗 → care_guide.md。"""
        from app.graph import run_graph
        from app.state.customer_state import create_initial_state

        state = run_graph(create_initial_state(
            session_id="rag-care", user_message="防晒衣怎么洗",
        ))
        sr = state.get("skill_result", {}) or {}
        sources = [e["source_file"] for e in sr.get("evidence", [])]
        assert "care_guide.md" in sources

    def test_refund_still_policy(self):
        """退款不受 RAG provider 影响。"""
        from app.graph import run_graph
        from app.state.customer_state import create_initial_state

        state = run_graph(create_initial_state(
            session_id="rag-rf", user_message="质量太差了我要退款",
        ))
        assert state["selected_skill"] == "refund_skill"
        assert state["policy_decision"] == "retention"
