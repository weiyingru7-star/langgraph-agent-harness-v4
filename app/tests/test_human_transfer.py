"""
测试: 转人工流程

验证转人工规则的触发条件是否正确。
"""


def test_escalation_policy_imports():
    """验证转人工规则模块可正常导入。"""
    from app.policies.escalation_policy import should_escalate

    # 默认情况不应转人工
    assert not should_escalate(
        emotion_score=0.0,
        user_requested_human=False,
        intent="greeting",
        errors=[],
    )
