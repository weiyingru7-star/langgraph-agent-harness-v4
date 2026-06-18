"""
测试: 纯文字输入场景

验证纯文字输入的完整处理流程是否正常。
"""


def test_text_only_imports():
    """验证必要模块可正常导入。"""
    from app.state.customer_state import create_initial_state

    state = create_initial_state(
        session_id="test-001",
        user_message="你好",
    )
    assert state["modality"] == "unknown"
    assert state["customer_stage"] == "unknown"
