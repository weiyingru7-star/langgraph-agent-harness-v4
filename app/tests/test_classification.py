"""意图/情绪/客户阶段分类节点的测试（Phase 4.2）。"""

from app.graph import run_graph
from app.state.customer_state import create_initial_state


def _node_names(state):
    return [entry["node"] for entry in state["logs"]]


class TestClassification:
    """8 个场景的分类结果测试。"""

    def test_logistics_anxious(self):
        """我的快递怎么还没到 → logistics_question, anxious, in_sale"""
        state = run_graph(create_initial_state(
            session_id="t1", user_message="我的快递怎么还没到",
        ))
        assert state["intent"] == "logistics_question"
        assert state["emotion"] == "anxious"
        assert state["customer_stage"] == "in_sale"

    def test_refund_angry(self):
        """质量太差了我要退款 → refund_request, angry, after_sale"""
        state = run_graph(create_initial_state(
            session_id="t2", user_message="质量太差了我要退款",
        ))
        assert state["intent"] == "refund_request"
        assert state["emotion"] == "angry"
        assert state["customer_stage"] == "after_sale"

    def test_product_question(self):
        """这个衣服是什么材质 → product_question, neutral, pre_sale"""
        state = run_graph(create_initial_state(
            session_id="t3", user_message="这个衣服是什么材质",
        ))
        assert state["intent"] == "product_question"
        assert state["emotion"] == "neutral"
        assert state["customer_stage"] == "pre_sale"

    def test_recommendation_or_product(self):
        """适合夏天骑车穿吗 → recommendation 或 product_question"""
        state = run_graph(create_initial_state(
            session_id="t4", user_message="适合夏天骑车穿吗",
        ))
        assert state["intent"] in ("product_question", "recommendation")
        assert state["emotion"] == "neutral"
        assert state["customer_stage"] == "pre_sale"

    def test_human_angry(self):
        """气死了，我要人工 → human_request, angry, Phase 5 触发转人工"""
        state = run_graph(create_initial_state(
            session_id="t5", user_message="气死了，我要人工",
        ))
        assert state["intent"] == "human_request"
        assert state["emotion"] == "angry"
        assert state["customer_stage"] in ("unknown", "after_sale")
        # Phase 5 开始 need_human 由 escalation_policy 决定
        # human_request + angry(0.9) → need_human = True

    def test_exchange_request(self):
        """我要换个尺码 → exchange_request, after_sale"""
        state = run_graph(create_initial_state(
            session_id="t6", user_message="我要换个尺码",
        ))
        assert state["intent"] == "exchange_request"
        assert state["customer_stage"] == "after_sale"

    def test_complaint_angry(self):
        """投诉 → complaint, angry, after_sale"""
        state = run_graph(create_initial_state(
            session_id="t7", user_message="你们这个太垃圾了，我要投诉",
        ))
        assert state["intent"] == "complaint"
        assert state["emotion"] == "angry"
        assert state["customer_stage"] == "after_sale"

    def test_smalltalk(self):
        """你好，在吗 → smalltalk, neutral, unknown"""
        state = run_graph(create_initial_state(
            session_id="t8", user_message="你好，在吗",
        ))
        assert state["intent"] == "smalltalk"
        assert state["emotion"] == "neutral"
        assert state["customer_stage"] == "unknown"


class TestLogs:
    """logs 包含分类节点。"""

    def test_logs_contain_classification_nodes(self):
        state = run_graph(create_initial_state(
            session_id="t", user_message="质量太差了我要退款",
        ))
        names = _node_names(state)
        assert "classify_intent" in names
        assert "classify_emotion" in names
        assert "classify_stage" in names
