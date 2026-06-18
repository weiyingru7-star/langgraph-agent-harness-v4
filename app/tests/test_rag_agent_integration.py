"""RAG Agent 集成测试（Phase 10.17-B）。"""

from app.graph import run_graph
from app.memory.conversation_memory import clear_memory
from app.state.customer_state import create_initial_state


def setup_function():
    clear_memory()


class TestRAGAgentIntegration:
    """RAG 接入 Agent 主流程后的集成测试。"""

    def test_refund_policy_question(self):
        """"超过7天还能退吗" → RAG, evidence 含 refund_policy.md。"""
        state = run_graph(create_initial_state(
            session_id="rag-1", user_message="超过7天还能退吗",
        ))
        assert state["selected_skill"] == "knowledge_qa_skill"
        sr = state.get("skill_result", {}) or {}
        assert sr.get("source") == "rag"
        assert sr.get("matched") is True
        assert len(sr.get("evidence", [])) > 0
        assert sr["evidence"][0]["source_file"] == "refund_policy.md"

    def test_care_guide_question(self):
        """"防晒衣怎么洗" → RAG, evidence 含 care_guide.md。"""
        state = run_graph(create_initial_state(
            session_id="rag-2", user_message="防晒衣怎么洗",
        ))
        assert state["selected_skill"] == "knowledge_qa_skill"
        sr = state.get("skill_result", {}) or {}
        assert sr.get("source") == "rag"
        sources = [e["source_file"] for e in sr.get("evidence", [])]
        assert "care_guide.md" in sources

    def test_shipping_faq_question(self):
        """"多久发货" → 走 RAG 或 logistics 均可，但不应 smalltalk。"""
        state = run_graph(create_initial_state(
            session_id="rag-3", user_message="多久发货",
        ))
        # "发货"关键词会命中 logistics_question intent
        r = state["reply"] or ""
        assert "48" in r or "发货" in r or "物流" in r or "快递" in r
        assert state["reply"] is not None

    def test_product_size_still_structured(self):
        """尺码问题仍走 product_qa_skill，不走 RAG。"""
        state = run_graph(create_initial_state(
            session_id="rag-4", user_message="运动外套有什么尺码",
        ))
        assert state["selected_skill"] == "product_qa_skill"
        r = state["reply"] or ""
        assert "M" in r or "XL" in r

    def test_price_still_structured(self):
        """价格问题仍走 product_qa_skill。"""
        state = run_graph(create_initial_state(
            session_id="rag-5", user_message="防晒衣多少钱",
        ))
        assert state["selected_skill"] == "product_qa_skill"
        r = state["reply"] or ""
        assert "129" in r or "199" in r or "元" in r

    def test_refund_still_policy(self):
        """"我要退款" 仍走 refund_skill + policy。"""
        state = run_graph(create_initial_state(
            session_id="rag-6", user_message="我要退款",
        ))
        assert state["selected_skill"] == "refund_skill"
        assert state["policy_decision"] == "retention"

    def test_rag_evidence_has_source_file(self):
        """RAG 回复中的 evidence 包含 source_file。"""
        state = run_graph(create_initial_state(
            session_id="rag-7", user_message="保养注意事项是什么",
        ))
        assert state["selected_skill"] == "knowledge_qa_skill"
        sr = state.get("skill_result", {}) or {}
        for ev in sr.get("evidence", []):
            assert "source_file" in ev
            assert "score" in ev

    def test_rag_reply_contains_evidence(self):
        """RAG 回复末尾标注来源。"""
        state = run_graph(create_initial_state(
            session_id="rag-8", user_message="超过7天还能退吗",
        ))
        r = state["reply"] or ""
        assert "refund_policy" in r or "来源" in r or "知识库" in r

    def test_contact_after_sale_goes_rag(self):
        """"怎么联系售后" → knowledge_qa_skill。"""
        state = run_graph(create_initial_state(
            session_id="rag-9", user_message="怎么联系售后",
        ))
        assert state["selected_skill"] == "knowledge_qa_skill"
