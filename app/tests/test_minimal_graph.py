"""最小 LangGraph 流程的测试（Phase 3.2）。"""

from app.graph import run_graph
from app.state.customer_state import create_initial_state

# 所有测试共享的日志节点名列表
EXPECTED_NODES = ["parse_input", "decide_modality", "analyze_text", "save_log"]


def _node_names(state):
    """提取 logs 中的节点名列表，便于断言。"""
    return [entry["node"] for entry in state["logs"]]


class TestTextOnly:
    """纯文本输入场景。"""

    def test_modality(self):
        state = run_graph(create_initial_state(
            session_id="t", user_message="我的快递怎么还没到",
        ))
        assert state["modality"] == "text_only"

    def test_text_analysis_not_none(self):
        state = run_graph(create_initial_state(
            session_id="t", user_message="我的快递怎么还没到",
        ))
        assert state["text_analysis"] is not None

    def test_logs_contain_all_nodes(self):
        state = run_graph(create_initial_state(
            session_id="t", user_message="我的快递怎么还没到",
        ))
        names = _node_names(state)
        for node in EXPECTED_NODES:
            assert node in names, f"缺少节点：{node}"


class TestImageOnly:
    """纯图片输入场景。"""

    def test_modality(self):
        state = run_graph(create_initial_state(
            session_id="t", image_url="https://example.com/test.jpg",
        ))
        assert state["modality"] == "image_only"

    def test_text_analysis_is_none(self):
        state = run_graph(create_initial_state(
            session_id="t", image_url="https://example.com/test.jpg",
        ))
        assert state["text_analysis"] is None

    def test_logs_contain_all_nodes(self):
        state = run_graph(create_initial_state(
            session_id="t", image_url="https://example.com/test.jpg",
        ))
        names = _node_names(state)
        for node in EXPECTED_NODES:
            assert node in names, f"缺少节点：{node}"


class TestTextWithImage:
    """图文混合输入场景。"""

    def test_modality(self):
        state = run_graph(create_initial_state(
            session_id="t",
            user_message="这个破了能退吗",
            image_url="https://example.com/broken.jpg",
        ))
        assert state["modality"] == "text_with_image"

    def test_text_analysis_not_none(self):
        state = run_graph(create_initial_state(
            session_id="t",
            user_message="这个破了能退吗",
            image_url="https://example.com/broken.jpg",
        ))
        assert state["text_analysis"] is not None

    def test_logs_contain_all_nodes(self):
        state = run_graph(create_initial_state(
            session_id="t",
            user_message="这个破了能退吗",
            image_url="https://example.com/broken.jpg",
        ))
        names = _node_names(state)
        for node in EXPECTED_NODES:
            assert node in names, f"缺少节点：{node}"


class TestEmptyInput:
    """空输入场景。"""

    def test_modality(self):
        state = run_graph(create_initial_state(
            session_id="t", user_message="",
        ))
        assert state["modality"] == "unknown"

    def test_text_analysis_is_none(self):
        state = run_graph(create_initial_state(
            session_id="t", user_message="",
        ))
        assert state["text_analysis"] is None

    def test_errors_not_added(self):
        """空输入不应产生错误。"""
        state = run_graph(create_initial_state(
            session_id="t", user_message="",
        ))
        assert state["errors"] == []
