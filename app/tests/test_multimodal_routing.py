"""多模态路由测试（Phase 7.2）。"""

from app.graph import run_graph
from app.memory.conversation_memory import clear_memory
from app.state.customer_state import create_initial_state


def _node_names(state):
    return [entry["node"] for entry in state["logs"]]


class TestImageOnly:
    """纯图片不调用多模态。"""

    def setup_method(self):
        clear_memory()

    def test_modality(self):
        state = run_graph(create_initial_state(
            session_id="t1", image_url="https://example.com/broken.jpg",
        ))
        assert state["modality"] == "image_only"

    def test_no_multimodal(self):
        state = run_graph(create_initial_state(
            session_id="t1", image_url="https://example.com/broken.jpg",
        ))
        assert state["multimodal_analysis"] is None
        assert state["selected_skill"] is None
        assert state["skill_result"]["action"] == "image_clarification"
        assert state["need_human"] is False

    def test_reply(self):
        state = run_graph(create_initial_state(
            session_id="t1", image_url="https://example.com/broken.jpg",
        ))
        assert "请问您想咨询这张图片里的什么问题" in state["reply"]


class TestTextWithImage:
    """图文混合调用 mock 多模态。"""

    def setup_method(self):
        clear_memory()

    def test_modality_and_analysis(self):
        state = run_graph(create_initial_state(
            session_id="t2",
            user_message="这个破了能退吗",
            image_url="https://example.com/broken.jpg",
        ))
        assert state["modality"] == "text_with_image"
        assert state["multimodal_analysis"] is not None
        assert state["multimodal_analysis"].get("is_mock") is True

    def test_intent_and_skill(self):
        state = run_graph(create_initial_state(
            session_id="t2",
            user_message="这个破了能退吗",
            image_url="https://example.com/broken.jpg",
        ))
        assert state["intent"] == "refund_request"
        assert state["selected_skill"] == "refund_skill"
        assert state["reply"]


class TestPrevTextCurrentImage:
    """先文字后图片 — memory 合并。"""

    def setup_method(self):
        clear_memory()

    def test_prev_text_and_image(self):
        # 第一轮：纯文字
        run_graph(create_initial_state(
            session_id="install-session",
            user_message="这个怎么安装",
        ))
        # 第二轮：纯图片，从 memory 读取上轮文字
        state = run_graph(create_initial_state(
            session_id="install-session",
            image_url="https://example.com/install.jpg",
        ))
        assert state["modality"] == "text_with_image"
        assert state["multimodal_analysis"] is not None
        assert state["intent"] == "product_question"
        assert state["selected_skill"] == "product_qa_skill"
        assert state["reply"]


class TestTextOnly:
    """普通纯文本流程不被破坏。"""

    def setup_method(self):
        clear_memory()

    def test_logistics(self):
        state = run_graph(create_initial_state(
            session_id="t4", user_message="我的快递怎么还没到",
        ))
        assert state["modality"] == "text_only"
        assert state["selected_skill"] == "logistics_skill"
        assert "物流" in state["reply"] or "快递" in state["reply"]


class TestLogs:
    """logs 包含多模态节点。"""

    def setup_method(self):
        clear_memory()

    def test_multimodal_logs(self):
        state = run_graph(create_initial_state(
            session_id="t",
            user_message="这个破了能退吗",
            image_url="https://example.com/broken.jpg",
        ))
        names = _node_names(state)
        assert "analyze_multimodal" in names
