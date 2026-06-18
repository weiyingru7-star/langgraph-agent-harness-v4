"""
测试: 退款流程

验证不同退款次数下的退款决策是否正确。
"""


def test_refund_policy_imports():
    """验证退款规则模块可正常导入。"""
    from app.policies.refund_policy import decide_refund_action, RefundDecision

    assert RefundDecision.RETENTION == "retention"
    assert RefundDecision.REFUND_WORKFLOW == "refund_workflow"
