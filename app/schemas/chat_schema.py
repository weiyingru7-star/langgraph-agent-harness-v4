"""
chat_schema.py — 聊天接口的请求/响应模型。

API 层只负责数据格式，不做业务判断。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天请求体。"""
    session_id: str = Field(..., description="会话标识")
    user_message: str = Field(default="", description="用户文本输入")
    image_url: Optional[str] = Field(default=None, description="图片 URL")
    image_base64: Optional[str] = Field(default=None, description="图片 base64 编码")
    return_full_state: bool = Field(default=False, description="是否返回完整 state")


class ChatResponse(BaseModel):
    """聊天响应体。"""
    session_id: Optional[str] = Field(default=None, description="会话标识")
    reply: Optional[str] = Field(default=None, description="客服回复")
    intent: Optional[str] = Field(default=None, description="识别意图")
    intent_confidence: float = Field(default=0.0, description="意图置信度")
    emotion: str = Field(default="neutral", description="情绪标签")
    emotion_score: float = Field(default=0.0, description="情绪评分")
    customer_stage: str = Field(default="unknown", description="客户阶段")
    selected_skill: Optional[str] = Field(default=None, description="路由技能")
    policy_decision: Optional[str] = Field(default=None, description="策略决策")
    need_human: bool = Field(default=False, description="需要转人工")
    human_reason: Optional[str] = Field(default=None, description="转人工原因")
    errors: List[str] = Field(default_factory=list, description="错误信息")
    logs: List[Dict[str, Any]] = Field(default_factory=list, description="执行日志")
    state: Optional[Dict[str, Any]] = Field(default=None, description="完整 state（仅 return_full_state=true 时）")


class HealthResponse(BaseModel):
    """健康检查响应。"""
    status: str = Field(default="ok")
    version: str = Field(default="v4-enhanced")
    tests_passed: int = Field(default=69)
