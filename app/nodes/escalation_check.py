"""
escalation_check.py — 转人工检查节点

职责：调用 escalation_policy 判断是否需要转人工。
      Phase 5 开始 need_human 由 escalation_policy 决定。
"""

from datetime import datetime

from app.policies.escalation_policy import decide_escalation
from app.state.customer_state import CustomerServiceState


def escalation_check(state: CustomerServiceState) -> dict:
    """
    检查是否需要转人工。

    读取字段：intent, emotion_score, errors
    写入字段：need_human, human_reason, logs

    Args:
        state: 当前状态

    Returns:
        包含 need_human, human_reason, logs 的部分 state dict
    """
    # 调用 escalation_policy 决策
    policy_result = decide_escalation(state)

    updated_logs = list(state["logs"])
    updated_logs.append({
        "node": "escalation_check",
        "summary": (
            f"need_human={policy_result['need_human']}"
            + (f", reason={policy_result['human_reason']}" if policy_result['human_reason'] else "")
        ),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {
        "need_human": policy_result["need_human"],
        "human_reason": policy_result["human_reason"],
        "logs": updated_logs,
    }
