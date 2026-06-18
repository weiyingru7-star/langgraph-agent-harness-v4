"""
generate_reply.py — 回复生成节点

职责：根据 skill_result、policy_decision、need_human 等字段
      生成结构化客服回复。第一版用模板，不调用真实 LLM。
"""

from datetime import datetime

from app.state.customer_state import CustomerServiceState


def generate_reply(state: CustomerServiceState) -> dict:
    """
    生成给用户的回复文本。

    读取字段：intent, selected_skill, skill_result, policy_decision,
             need_human, human_reason, emotion, customer_stage, errors
    写入字段：reply, logs

    Args:
        state: 当前状态

    Returns:
        包含 reply 和 logs 的部分 state dict
    """
    reply = _build_reply(state)

    updated_logs = list(state["logs"])
    updated_logs.append({
        "node": "generate_reply",
        "summary": f"reply_length={len(reply)}, need_human={state['need_human']}",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {"reply": reply, "logs": updated_logs}


def _build_reply(state: CustomerServiceState) -> str:
    """根据 state 字段选择合适的回复模板。"""

    # 优先级 1：need_human → 转人工
    if state["need_human"]:
        return _human_transfer_reply(state)

    # 优先级 2：根据 selected_skill 选择模板
    skill = state["selected_skill"]
    sr = state["skill_result"] or {}
    action = sr.get("action", "")

    if skill == "logistics_skill":
        return _logistics_reply(sr)
    elif skill == "refund_skill":
        return _refund_reply(state)
    elif skill == "product_qa_skill":
        return _product_qa_reply(sr)
    elif skill == "recommendation_skill":
        return _recommendation_reply(sr)
    elif skill == "exchange_skill":
        return _exchange_reply()
    elif skill == "complaint_skill":
        return _complaint_reply()
    elif action == "smalltalk_fallback":
        return "您好，我在的。请问有什么可以帮您？"
    else:
        return _fallback_reply()


# ========== 模板函数 ==========


def _human_transfer_reply(state: CustomerServiceState) -> str:
    """need_human=True 时的转人工回复。"""
    reason = state.get("human_reason")
    lines = ["我理解您现在需要人工帮助。"]
    if reason:
        lines.append(f"问题说明：{reason}")
    lines.append("正在为您转接人工客服，请稍候。")
    lines.append("我会把当前问题和已识别的信息一起交给人工客服，方便他们快速为您处理。")
    return "\n".join(lines)


def _logistics_reply(skill_result: dict) -> str:
    """物流查询回复。"""
    order = skill_result.get("order_info", {}) if skill_result else {}
    tracking = order.get("tracking_no", "—")
    status = order.get("status", "—")
    eta = order.get("eta", "—")
    return (
        f"感谢您的耐心等待，我来帮您查看一下物流信息。\n"
        f"您的快递已发货，单号 {tracking}，\n"
        f'目前状态是"{status}"，{eta}。\n'
        f"请您耐心等待，如有其他问题随时联系我们。"
    )


def _refund_reply(state: CustomerServiceState) -> str:
    """退款处理回复。保留策略支持 retention / refund_workflow / direct_refund。"""
    decision = state.get("policy_decision", "retention")
    if decision == "retention":
        return (
            f"非常抱歉让您有不好的体验，我先帮您看一下这个问题。\n"
            f"目前系统判断这是首次退款请求，我们会优先帮您确认问题原因，"
            f"并尝试给出补偿或处理方案。\n"
            f"您可以先把具体质量问题发我，我会继续帮您判断是换货、补偿"
            f"还是进入退款流程。\n"
            f"如果您仍然坚持退款，我们会继续为您处理。"
        )
    elif decision == "refund_workflow":
        return (
            f"好的，已为您记录第二次退款请求。\n"
            f"系统已启动退款流程，我们的工作人员会尽快处理。\n"
            f"退款金额将原路返回，预计 3-5 个工作日到账。\n"
            f"如有其他问题欢迎随时联系我们。"
        )
    else:
        return (
            f"已记录您的退款请求。\n"
            f"由于多次退款请求，此问题需要人工确认处理。\n"
            f"正在为您转接人工客服，他们会进一步核实并处理。\n"
            f"请稍候。"
        )


def _product_qa_reply(skill_result: dict) -> str:
    """商品问答回复。"""
    product = skill_result.get("product_info", {}) if skill_result else {}
    name = product.get("product_name", "—")
    material = product.get("material", "—")
    size = product.get("size", "—")
    features = product.get("features", [])
    scene = product.get("suitable_scene", "—")
    return (
        f"您咨询的商品信息如下：\n"
        f"商品名称：{name}\n"
        f"材质：{material}\n"
        f"尺码：{size}\n"
        f"特点：{'、'.join(features)}\n"
        f"适用场景：{scene}\n"
        f"如果您需要了解更多信息，欢迎继续咨询。"
    )


def _recommendation_reply(skill_result: dict) -> str:
    """商品推荐回复。"""
    product = skill_result.get("product_info", {}) if skill_result else {}
    name = product.get("product_name", "—")
    features = product.get("features", [])
    scene = product.get("suitable_scene", "—")
    return (
        f"根据您的需求，我为您推荐以下商品：\n"
        f"{name}\n"
        f"特点：{'、'.join(features)}\n"
        f"适用场景：{scene}\n"
        f"如果您对这款商品感兴趣，可以告诉我，我可以提供更多详情。"
    )


def _exchange_reply() -> str:
    """换货处理回复。"""
    return (
        f"好的，我来帮您处理换货。\n"
        f"已进入换货流程，下一步需要您确认以下信息：\n"
        f"1. 订单号\n"
        f"2. 您想要更换的尺码/颜色\n"
        f"3. 收货地址是否变更\n"
        f"请提供相关信息，我会继续为您处理。"
    )


def _complaint_reply() -> str:
    """投诉处理回复。"""
    return (
        f"非常抱歉给您带来这么不好的体验，我理解您现在的心情。\n"
        f"已经记录您的投诉信息，我们会高度重视。\n"
        f"由于投诉需要专人处理，我将为您转接人工客服，"
        f"他们会进一步跟进您的问题。\n"
        f"请您耐心等待，感谢您的反馈。"
    )


def _fallback_reply() -> str:
    """兜底回复。"""
    return (
        "我已经收到您的问题了，请您再补充一下具体想咨询的内容，"
        "我会继续帮您处理。"
    )
