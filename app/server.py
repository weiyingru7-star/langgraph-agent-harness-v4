"""
server.py — FastAPI 应用入口。

提供 HTTP 接口，不包含业务逻辑。
"""

from fastapi import FastAPI

from app.api.chat_api import handle_chat
from app.schemas.chat_schema import ChatRequest, ChatResponse, HealthResponse

app = FastAPI(title="LangGraph Agent Harness", version="v4-enhanced")


@app.get("/api/health", response_model=HealthResponse)
def health():
    """健康检查。"""
    return HealthResponse()


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """聊天接口。"""
    return handle_chat(req)
