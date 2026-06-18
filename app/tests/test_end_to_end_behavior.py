"""端到端行为审计测试（Phase 10.4.2）。"""

from app.graph import run_graph
from app.memory.conversation_memory import clear_memory
from app.state.customer_state import create_initial_state


def setup_function():
    """每个测试前清理 memory。"""
    clear_memory()


class TestEndToEndBehavior:
    """10 个场景的全链路行为测试。"""

    def test_product_material(self):
        """商品材质 — 必须回复材质相关内容，不能出现运动鞋/EVA。"""
        state = run_graph(create_initial_state(
            session_id="e2e-mat", user_message="这个衣服是什么材质",
        ))
        assert state["intent"] == "product_question"
        assert state["selected_skill"] == "product_qa_skill"
        r = state["reply"] or ""
        assert "材质" in r or "锦纶" in r or "面料" in r
        for bad in ["运动鞋", "EVA", "鞋底", "39-44"]:
            assert bad not in r, f"回复含不当词: {bad}"

    def test_product_size(self):
        """商品尺码 — 不能回 smalltalk。"""
        state = run_graph(create_initial_state(
            session_id="e2e-size", user_message="有什么码数",
        ))
        assert state["intent"] == "product_question", f"应为 product_question，实际为 {state['intent']}"
        assert state["selected_skill"] == "product_qa_skill"
        r = state["reply"] or ""
        assert "M/L" in r or "尺码" in r or "码" in r

    def test_product_age_suit(self):
        """年龄适合 — 无商品名时澄清，有 history 时结合商品回答。"""
        state = run_graph(create_initial_state(
            session_id="e2e-age", user_message="30岁适合吗",
        ))
        assert state["intent"] == "product_question"
        assert state["selected_skill"] == "product_qa_skill"
        r = state["reply"] or ""
        # 没有商品名时返回澄清，不崩溃
        assert "商品名称" in r or "哪款商品" in r or "适合" in r or "型号" in r

    def test_recommendation_conservative(self):
        """推荐 — 不能凭空推不存在商品。"""
        state = run_graph(create_initial_state(
            session_id="e2e-rec", user_message="有没有推荐",
        ))
        assert state["intent"] == "recommendation"
        assert state["selected_skill"] == "recommendation_skill"
        r = state["reply"] or ""
        assert "运动鞋" not in r
        assert "推荐" in r

    def test_logistics(self):
        """物流查询 — 回复含物流信息。"""
        state = run_graph(create_initial_state(
            session_id="e2e-log", user_message="我的快递怎么还没到",
        ))
        assert state["selected_skill"] == "logistics_skill"
        r = state["reply"] or ""
        assert "物流" in r or "快递" in r or "单号" in r

    def test_pure_image(self):
        """纯图片 — 只能追问。"""
        state = run_graph(create_initial_state(
            session_id="e2e-img", image_url="https://example.com/test.jpg",
        ))
        assert state["modality"] == "image_only"
        assert state["selected_skill"] is None
        r = state["reply"] or ""
        assert "请问您想咨询这张图片里的什么问题" in r

    def test_text_with_image_refund(self):
        """图文售后 — 走退款流程。"""
        state = run_graph(create_initial_state(
            session_id="e2e-ti",
            user_message="这个破了能退吗",
            image_url="https://example.com/test.jpg",
        ))
        assert state["modality"] == "text_with_image"
        assert state["selected_skill"] == "refund_skill"
        r = state["reply"] or ""
        assert "退款" in r or "抱歉" in r or "换货" in r or "赔偿" in r

    def test_smalltalk(self):
        """闲聊 — 不走业务 skill。"""
        state = run_graph(create_initial_state(
            session_id="e2e-st", user_message="你好，在吗",
        ))
        assert state["intent"] == "smalltalk"
        assert state["selected_skill"] is None

    def test_complaint(self):
        """投诉 — 转人工。"""
        state = run_graph(create_initial_state(
            session_id="e2e-cp", user_message="你们这个太垃圾了，我要投诉",
        ))
        assert state["intent"] == "complaint"
        assert state["need_human"] is True

    def test_refund_retention(self):
        """退款 — 走 retention + 转人工。"""
        state = run_graph(create_initial_state(
            session_id="e2e-rf", user_message="质量太差了我要退款",
        ))
        assert state["intent"] == "refund_request"
        assert state["selected_skill"] == "refund_skill"
        assert state["policy_decision"] == "retention"
