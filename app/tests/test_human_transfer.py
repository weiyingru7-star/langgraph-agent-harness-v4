"""
测试：转人工流程

验证转人工规则的触发条件是否正确。
Phase 5 中函数名改为 decide_escalation。
"""


def test_escalation_policy_imports():
    """验证转人工规则模块可正常导入。"""
    from app.policies.escalation_policy import decide_escalation
    from app.state.customer_state import create_initial_state

    # 默认情况不应转人工
    state = create_initial_state(session_id="test", user_message="你好")
    result = decide_escalation(state)
    assert result["need_human"] is False
