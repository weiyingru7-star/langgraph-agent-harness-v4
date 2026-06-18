"""
refund_policy.py — 退款规则

业务规则（来自 CLAUDE.md）：
    第一次退款请求 → retention（挽留）
    第二次明确退款请求 → refund_workflow（执行退款流程）
    第三次退款请求 → direct_refund_or_human_confirm（直接退款或人工确认）

重要：
    不要把退款规则写进 prompt。
    不要让 LLM 直接决定是否退款。
    退款决策必须由此函数生成。
"""


def decide_refund_action(refund_count: int = 1) -> dict:
    """
    根据退款次数决定退款处理方式。

    Args:
        refund_count: 该用户历史退款次数（第一版 mock 为 1）

    Returns:
        dict: {"decision": str, "reason": str}
    """
    if refund_count >= 3:
        return {
            "decision": "direct_refund_or_human_confirm",
            "reason": "多次退款请求，建议直接退款或人工确认",
        }
    elif refund_count == 2:
        return {
            "decision": "refund_workflow",
            "reason": "二次明确退款，进入退款流程",
        }
    else:
        return {
            "decision": "retention",
            "reason": "首次退款，先进入挽留流程",
        }
