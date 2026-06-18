"""
refund_skill.py — 退款处理技能

职责：处理退款请求，根据 policy_decision 执行挽留或退款。
       policy_decision 由 route_to_skill 在调用本技能之前写入 state。
"""


def run_refund_skill(state: dict) -> dict:
    """执行退款处理，基于 refund_policy 的决策结果。"""
    decision = state["policy_decision"]
    messages = {
        "retention": "首次退款，先进入挽留流程",
        "refund_workflow": "二次明确退款，进入退款流程",
        "direct_refund_or_human_confirm": "多次退款请求，建议直接退款或人工确认",
    }
    return {
        "skill_result": {
            "action": decision,
            "message": messages.get(decision, "退款请求已处理"),
        }
    }
