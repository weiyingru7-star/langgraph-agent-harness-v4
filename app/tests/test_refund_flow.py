"""
测试：退款流程

验证不同退款次数下的退款决策是否正确。
Phase 5 中 RefundDecision Enum 已改为 decide_refund_action 函数。
"""


def test_refund_policy_imports():
    """验证退款规则模块可正常导入。"""
    from app.policies.refund_policy import decide_refund_action

    result = decide_refund_action(refund_count=1)
    assert result["decision"] == "retention"
    assert result["reason"] != ""

    result = decide_refund_action(refund_count=2)
    assert result["decision"] == "refund_workflow"

    result = decide_refund_action(refund_count=3)
    assert result["decision"] == "direct_refund_or_human_confirm"
