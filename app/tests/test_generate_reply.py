"""generate_reply 回复生成测试（Phase 6.2）。"""

from app.graph import run_graph
from app.nodes.generate_reply import _fallback_reply
from app.state.customer_state import create_initial_state


def _node_names(state):
    return [entry["node"] for entry in state["logs"]]


class TestGenerateReply:
    """回复生成场景测试。"""

    def test_logistics_reply(self):
        """物流查询 → reply 包含物流信息"""
        state = run_graph(create_initial_state(
            session_id="t1", user_message="我的快递怎么还没到",
        ))
        assert state["selected_skill"] == "logistics_skill"
        assert state["reply"]
        assert "物流" in state["reply"] or "快递" in state["reply"]
        assert "SF1234567890" in state["reply"] or "预计" in state["reply"]

    def test_refund_retention_reply(self):
        """退款挽留 → need_human 时回复为转人工"""
        state = run_graph(create_initial_state(
            session_id="t2", user_message="质量太差了我要退款",
        ))
        assert state["selected_skill"] == "refund_skill"
        assert state["policy_decision"] == "retention"
        assert state["reply"]
        # emotion_score=0.9 > 0.85 → need_human=True → 转人工回复
        assert "人工" in state["reply"]
        assert "已经退款" not in state["reply"]
        assert "退款已完成" not in state["reply"]

    def test_product_qa_reply(self):
        """商品咨询 → reply 包含商品材质"""
        state = run_graph(create_initial_state(
            session_id="t3", user_message="这个衣服是什么材质",
        ))
        assert state["selected_skill"] == "product_qa_skill"
        assert state["reply"]
        assert any(w in state["reply"] for w in ["材质", "透气", "面料", "防晒"])

    def test_human_reply(self):
        """人工请求 → reply 包含转人工"""
        state = run_graph(create_initial_state(
            session_id="t4", user_message="气死了，我要人工",
        ))
        assert state["selected_skill"] == "human_skill"
        assert state["need_human"] is True
        assert state["reply"]
        assert "人工" in state["reply"] or "转人工" in state["reply"]

    def test_complaint_reply(self):
        """投诉 → reply 包含投诉或人工"""
        state = run_graph(create_initial_state(
            session_id="t5", user_message="你们这个太垃圾了，我要投诉",
        ))
        assert state["selected_skill"] == "complaint_skill"
        assert state["need_human"] is True
        assert state["reply"]
        assert any(w in state["reply"] for w in ["投诉", "人工", "抱歉"])

    def test_exchange_reply(self):
        """换货 → reply 包含换货"""
        state = run_graph(create_initial_state(
            session_id="t6", user_message="我要换个尺码",
        ))
        assert state["selected_skill"] == "exchange_skill"
        assert state["reply"]
        assert any(w in state["reply"] for w in ["换货", "尺码"])

    def test_smalltalk_reply(self):
        """闲聊 → 固定兜底回复"""
        state = run_graph(create_initial_state(
            session_id="t7", user_message="你好，在吗",
        ))
        assert state["intent"] == "smalltalk"
        assert state["selected_skill"] is None
        assert state["skill_result"]["action"] == "smalltalk_fallback"
        assert state["need_human"] is False
        assert state["reply"] == "您好，我在的。请问有什么可以帮您？"


class TestLogs:
    """logs 包含 generate_reply。"""

    def test_logs_contain_generate_reply(self):
        state = run_graph(create_initial_state(
            session_id="t", user_message="质量太差了我要退款",
        ))
        names = _node_names(state)
        assert "generate_reply" in names


class TestFallback:
    """兜底回复测试。"""

    def test_fallback_reply_text(self):
        """兜底回复文本正确。"""
        reply = _fallback_reply()
        assert reply
        assert "再补充" in reply
        assert "继续帮您处理" in reply

    def test_fallback_reply_no_skill(self):
        """无 selected_skill 且非 smalltalk 时走兜底。"""
        from app.nodes.generate_reply import _build_reply
        state = create_initial_state(session_id="t", user_message="something")
        state["selected_skill"] = "unknown_skill"
        state["need_human"] = False
        state["skill_result"] = {"action": "unknown_action"}
        reply = _build_reply(state)
        assert reply
        assert "再补充" in reply
