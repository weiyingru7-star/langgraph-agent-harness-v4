"""
server.py — FastAPI 应用入口。

提供 HTTP 接口，不包含业务逻辑。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat_api import handle_chat
from app.schemas.chat_schema import ChatRequest, ChatResponse, HealthResponse

app = FastAPI(title="LangGraph Agent Harness", version="v4-enhanced")

# CORS — 允许 Next.js 开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health():
    """健康检查。"""
    return HealthResponse()


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """聊天接口。"""
    return handle_chat(req)
