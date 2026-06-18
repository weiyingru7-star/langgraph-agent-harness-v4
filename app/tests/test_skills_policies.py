"""Skill/Tool/Policy 集成测试（Phase 5.2）。"""

from app.graph import run_graph
from app.state.customer_state import create_initial_state


def _node_names(state):
    return [entry["node"] for entry in state["logs"]]


class TestSkillRouting:
    """技能路由测试。"""

    def test_logistics_query(self):
        """快递查询 → logistics_skill"""
        state = run_graph(create_initial_state(
            session_id="t1", user_message="我的快递怎么还没到",
        ))
        assert state["intent"] == "logistics_question"
        assert state["selected_skill"] == "logistics_skill"
        assert state["skill_result"]["action"] == "logistics_query"
        assert "order_info" in state["skill_result"]
        assert state["need_human"] is False

    def test_recommendation(self):
        """推荐 → recommendation_skill"""
        state = run_graph(create_initial_state(
            session_id="t1r", user_message="推荐一款好用的手机",
        ))
        assert state["intent"] == "recommendation"
        assert state["selected_skill"] == "recommendation_skill"
        assert "message" in state["skill_result"]
        # Phase 10: recommendation_skill 返回保守说明，不是具体商品
        assert "推荐" in state["skill_result"]["message"]
        assert state["need_human"] is False

    def test_first_refund(self):
        """质量太差了我要退款 → refund_skill"""
        state = run_graph(create_initial_state(
            session_id="t2", user_message="质量太差了我要退款",
        ))
        assert state["intent"] == "refund_request"
        assert state["selected_skill"] == "refund_skill"
        assert state["policy_decision"] == "retention"
        assert state["skill_result"]["action"] == "retention"
        # emotion_score=0.9 > 0.85 → need_human=True（Phase 5 预期行为）
        assert state["need_human"] is True

    def test_product_qa(self):
        """这个衣服是什么材质 → product_qa_skill"""
        state = run_graph(create_initial_state(
            session_id="t3", user_message="这个衣服是什么材质",
        ))
        assert state["intent"] == "product_question"
        assert state["selected_skill"] == "product_qa_skill"
        assert state["skill_result"]["action"] == "product_answer"
        # product_qa_skill 可能返回 matched_product / matched_faq / clarification
        sr = state["skill_result"]
        has_data = any(k in sr for k in ["matched_product", "matched_faq", "matched_product", "query_type"])
        assert has_data, f"skill_result 缺少商品/FAQ 数据: {sr}"
        assert state["need_human"] is False

    def test_human_request(self):
        """我要人工，太生气了 → human_skill"""
        state = run_graph(create_initial_state(
            session_id="t4", user_message="气死了，我要人工",
        ))
        assert state["intent"] == "human_request"
        assert state["selected_skill"] == "human_skill"
        assert state["need_human"] is True
        assert state["human_reason"] is not None

    def test_complaint(self):
        """投诉 → complaint_skill"""
        state = run_graph(create_initial_state(
            session_id="t5", user_message="你们这个太垃圾了，我要投诉",
        ))
        assert state["intent"] == "complaint"
        assert state["selected_skill"] == "complaint_skill"
        assert state["need_human"] is True
        assert state["human_reason"] is not None

    def test_exchange(self):
        """换货 → exchange_skill"""
        state = run_graph(create_initial_state(
            session_id="t6", user_message="我要换个尺码",
        ))
        assert state["intent"] == "exchange_request"
        assert state["selected_skill"] == "exchange_skill"
        assert state["skill_result"]["action"] == "exchange_flow"
        assert state["need_human"] is False

    def test_smalltalk(self):
        """闲聊 → 不走 skill"""
        state = run_graph(create_initial_state(
            session_id="t7", user_message="你好，在吗",
        ))
        assert state["intent"] == "smalltalk"
        assert state["selected_skill"] is None
        assert state["skill_result"]["action"] == "smalltalk_fallback"
        assert state["need_human"] is False


class TestLogs:
    """logs 包含新增节点。"""

    def test_logs_contain_new_nodes(self):
        state = run_graph(create_initial_state(
            session_id="t", user_message="质量太差了我要退款",
        ))
        names = _node_names(state)
        assert "route_to_skill" in names
        assert "escalation_check" in names
