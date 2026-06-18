"""
refund_policy.py — 退款规则

业务规则（来自 CLAUDE.md）:
    第一次退款请求 → retention（挽留）
    第二次明确退款请求 → refund_workflow（执行退款流程）
    第三次退款请求 → direct_refund_or_human_confirm（直接退款或人工确认）

重要:
    不要把退款规则写进 prompt。
    不要让 LLM 直接决定是否退款。
"""

from enum import Enum


class RefundDecision(str, Enum):
    """退款决策类型。"""
    RETENTION = "retention"                      # 挽留
    REFUND_WORKFLOW = "refund_workflow"          # 执行退款
    DIRECT_REFUND_OR_HUMAN = "direct_refund_or_human_confirm"  # 直接退款或人工


def decide_refund_action(refund_count: int) -> RefundDecision:
    """
    根据历史退款次数决定退款处理方式。

    Args:
        refund_count: 该用户历史退款次数

    Returns:
        退款决策类型
    """
    # TODO: 后续阶段实现完整退款逻辑
    if refund_count >= 2:
        return RefundDecision.DIRECT_REFUND_OR_HUMAN
    elif refund_count >= 1:
        return RefundDecision.REFUND_WORKFLOW
    return RefundDecision.RETENTION
