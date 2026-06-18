"""
route_to_skill.py — 路由节点

职责：根据 intent 选择对应的 skill 并执行，将结果写入 state。
      如果是 refund_request，先调用 refund_policy 再执行 skill。
      如果是 smalltalk，不调用任何 skill。
"""

from datetime import datetime

from app.policies.refund_policy import decide_refund_action
from app.skills.complaint_skill import run_complaint_skill
from app.skills.exchange_skill import run_exchange_skill
from app.skills.human_skill import run_human_skill
from app.skills.logistics_skill import run_logistics_skill
from app.skills.product_qa_skill import run_product_qa_skill
from app.skills.recommendation_skill import run_recommendation_skill
from app.skills.refund_skill import run_refund_skill
from app.state.customer_state import CustomerServiceState

# intent → (skill 函数, selected_skill 名称)
_ROUTE_MAP = {
    "product_question": (run_product_qa_skill, "product_qa_skill"),
    "recommendation": (run_recommendation_skill, "recommendation_skill"),
    "logistics_question": (run_logistics_skill, "logistics_skill"),
    "refund_request": (run_refund_skill, "refund_skill"),
    "exchange_request": (run_exchange_skill, "exchange_skill"),
    "complaint": (run_complaint_skill, "complaint_skill"),
    "human_request": (run_human_skill, "human_skill"),
}


def route_to_skill(state: CustomerServiceState) -> dict:
    """
    根据 intent 路由到对应 skill 并执行。

    读取字段：intent, user_message, emotion, customer_stage
    写入字段：selected_skill, skill_result, policy_decision（仅退款）, logs

    Args:
        state: 当前状态

    Returns:
        包含路由结果的部分 state dict
    """
    intent = state["intent"]
    result = {}

    # 特殊处理：image_only（纯图片无上轮文字）
    if state["modality"] == "image_only":
        result["selected_skill"] = None
        result["skill_result"] = {
            "action": "image_clarification",
        }
    elif intent in _ROUTE_MAP:
        skill_func, skill_name = _ROUTE_MAP[intent]

        # route_to_skill 负责设置 selected_skill
        result["selected_skill"] = skill_name

        # 如果是退货请求，先调用 refund_policy
        if intent == "refund_request":
            policy_result = decide_refund_action(refund_count=1)
            result["policy_decision"] = policy_result["decision"]
            # 把 policy_decision 合并到 state，供 skill 读取
            state["policy_decision"] = policy_result["decision"]

        # 执行 skill
        skill_output = skill_func(state)
        result["skill_result"] = skill_output["skill_result"]
    else:
        # smalltalk 或未识别兜底
        result["selected_skill"] = None
        result["skill_result"] = {"action": "smalltalk_fallback"}

    # 追加日志
    updated_logs = list(state["logs"])
    updated_logs.append({
        "node": "route_to_skill",
        "summary": f"selected_skill={result['selected_skill']}, intent={intent}",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })
    result["logs"] = updated_logs

    return result
