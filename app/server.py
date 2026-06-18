"""
server.py — FastAPI 应用入口。

提供 HTTP 接口，不包含业务逻辑。
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 加载 .env 配置文件（如存在）
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'\"")
            if key and value:
                os.environ.setdefault(key, value)

from app.api.chat_api import handle_chat
from app.schemas.chat_schema import ChatRequest, ChatResponse, HealthResponse

app = FastAPI(title="LangGraph Agent Harness", version="v4-enhanced")

# CORS — 允许 Next.js 开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://localhost:3002",
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
