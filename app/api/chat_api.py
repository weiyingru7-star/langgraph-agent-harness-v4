"""
chat_api.py — 聊天 API 路由。

职责：接收 HTTP 请求，调用 LangGraph Agent，返回结果。
      不包含业务判断。
"""

from app.graph import run_graph
from app.persistence import sqlite_store
from app.schemas.chat_schema import ChatRequest, ChatResponse, HealthResponse
from app.state.customer_state import create_initial_state


def handle_chat(req: ChatRequest) -> ChatResponse:
    """
    处理聊天请求。

    1. 创建 initial_state
    2. Context Loader: 读取历史消息写入 state
    3. 调用 run_graph
    4. 提取关键字段返回
    5. 持久化（失败不影响回复）
    """
    try:
        initial = create_initial_state(
            session_id=req.session_id,
            user_message=req.user_message,
            image_url=req.image_url,
            image_base64=req.image_base64,
        )

        # ── Context Loader：从 SQLite 读取历史消息 ──
        try:
            history = sqlite_store.get_messages(req.session_id, limit=10)
            if history:
                cleaned = [
                    {"role": m["role"], "content": m["content"]}
                    for m in history
                ]
                initial["conversation_history"] = cleaned
        except Exception as e:
            print(f"[context_loader] 读取历史失败: {e}")

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

    # ── 持久化（失败不影响 Agent 回复） ──
    persist_errors = []

    try:
        sqlite_store.save_message(req.session_id, "user", req.user_message, req.image_url)
    except Exception as e:
        persist_errors.append(f"保存用户消息失败: {e}")

    try:
        sqlite_store.save_message(req.session_id, "assistant", state.get("reply", ""))
    except Exception as e:
        persist_errors.append(f"保存回复失败: {e}")

    try:
        sqlite_store.save_agent_run(state)
    except Exception as e:
        persist_errors.append(f"保存 Agent 运行记录失败: {e}")

    try:
        sqlite_store.save_handoff_if_needed(state)
    except Exception as e:
        persist_errors.append(f"保存转人工记录失败: {e}")

    if persist_errors:
        resp.errors.extend(persist_errors)

    return resp
