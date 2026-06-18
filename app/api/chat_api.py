"""
chat_api.py — 聊天 API 路由。

职责：接收 HTTP 请求，调用 LangGraph Agent，返回结果。
      不包含业务判断。
"""

from app.graph import run_graph
from app.schemas.chat_schema import ChatRequest, ChatResponse, HealthResponse
from app.state.customer_state import create_initial_state


def handle_chat(req: ChatRequest) -> ChatResponse:
    """
    处理聊天请求。

    1. 创建 initial_state
    2. 调用 run_graph
    3. 提取关键字段返回
    """
    try:
        initial = create_initial_state(
            session_id=req.session_id,
            user_message=req.user_message,
            image_url=req.image_url,
            image_base64=req.image_base64,
        )
        state = run_graph(initial)
    except Exception as e:
        return ChatResponse(
            session_id=req.session_id,
            errors=[f"Agent 执行异常: {str(e)}"],
            logs=[],
        )

    resp = ChatResponse(
        session_id=state.get("session_id"),
        reply=state.get("reply"),
        intent=state.get("intent"),
        intent_confidence=state.get("intent_confidence", 0.0),
        emotion=state.get("emotion", "neutral"),
        emotion_score=state.get("emotion_score", 0.0),
        customer_stage=state.get("customer_stage", "unknown"),
        selected_skill=state.get("selected_skill"),
        policy_decision=state.get("policy_decision"),
        need_human=state.get("need_human", False),
        human_reason=state.get("human_reason"),
        errors=state.get("errors", []),
        logs=state.get("logs", []),
    )

    if req.return_full_state:
        resp.state = dict(state)

    return resp
