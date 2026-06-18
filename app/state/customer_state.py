"""
customer_state.py — CustomerServiceState 定义

本文件定义了整个客服 Agent 的全局状态结构（CustomerServiceState），
以及配套的枚举常量和工厂函数。

设计文档请参考 docs/STATE_DESIGN.md。
"""

from typing import Any, Dict, List, Optional, TypedDict

# ============================================================
# 枚举常量
#
# 定义成常量而非字符串字面量，避免后面各节点写散字符串。
# 后续节点（classify_intent、route_to_skill 等）统一引用这些常量。
# ============================================================

# --- modality（输入模态） ---
MODALITY_TEXT_ONLY = "text_only"              # 纯文本输入
MODALITY_IMAGE_ONLY = "image_only"            # 纯图片输入
MODALITY_TEXT_WITH_IMAGE = "text_with_image"  # 文本 + 图片输入
MODALITY_UNKNOWN = "unknown"                  # 尚未判断

# --- intent（用户意图） ---
INTENT_PRODUCT_QUESTION = "product_question"      # 商品咨询
INTENT_RECOMMENDATION = "recommendation"          # 寻求推荐
INTENT_LOGISTICS_QUESTION = "logistics_question"  # 物流查询
INTENT_REFUND_REQUEST = "refund_request"          # 退款请求
INTENT_EXCHANGE_REQUEST = "exchange_request"      # 换货请求
INTENT_COMPLAINT = "complaint"                    # 投诉
INTENT_HUMAN_REQUEST = "human_request"            # 要求转人工
INTENT_SMALLTALK = "smalltalk"                    # 闲聊/问候

# --- emotion（用户情绪） ---
EMOTION_NEUTRAL = "neutral"           # 平静
EMOTION_ANXIOUS = "anxious"           # 焦虑
EMOTION_ANGRY = "angry"               # 愤怒
EMOTION_DISAPPOINTED = "disappointed" # 失望
EMOTION_URGENT = "urgent"             # 急切

# --- customer_stage（客户阶段） ---
STAGE_PRE_SALE = "pre_sale"     # 售前（咨询商品）
STAGE_IN_SALE = "in_sale"       # 售中（订单进行中，如物流）
STAGE_AFTER_SALE = "after_sale" # 售后（退款/换货/投诉）
STAGE_UNKNOWN = "unknown"       # 未知


class CustomerServiceState(TypedDict):
    """客服 Agent 全局状态。

    所有 LangGraph 节点共同读写同一个 State 对象。
    TypedDict 版本，字段与 docs/STATE_DESIGN.md 保持一致。
    第一版追求最小可运行，后续商业版可升级为 Pydantic BaseModel。
    """

    # ========== A. 会话输入字段 ==========
    session_id: str
    """会话唯一标识，用于日志追踪和会话恢复。"""

    user_message: str
    """用户输入的文本内容。所有分析都基于此字段。"""

    image_url: Optional[str]
    """用户上传图片的 URL 地址。没有图片时为 None。"""

    image_base64: Optional[str]
    """用户上传图片的 base64 编码，用于多模态分析。没有图片时为 None。"""

    # ========== B. 输入类型判断字段 ==========
    modality: str
    """输入模态类型。决定后续走纯文本分析还是多模态分析路径。
    取值：MODALITY_TEXT_ONLY / MODALITY_IMAGE_ONLY / MODALITY_TEXT_WITH_IMAGE / MODALITY_UNKNOWN。"""

    # ========== C. 分析结果字段 ==========
    text_analysis: Optional[str]
    """LLM 对用户文本的分析摘要。包含对用户问题的理解和关键信息提取。"""

    multimodal_analysis: Optional[str]
    """LLM 对文本+图片的综合分析结果。纯文本输入时为 None。"""

    intent: Optional[str]
    """用户意图分类。路由决策的核心输入，决定调用哪个 skill。
    取值：INTENT_PRODUCT_QUESTION / INTENT_RECOMMENDATION / INTENT_LOGISTICS_QUESTION /
          INTENT_REFUND_REQUEST / INTENT_EXCHANGE_REQUEST / INTENT_COMPLAINT /
          INTENT_HUMAN_REQUEST / INTENT_SMALLTALK。"""

    intent_confidence: float
    """意图置信度（0.0~1.0）。反映 LLM 对意图判断的把握程度。"""

    emotion: str
    """用户情绪标签。帮助客服选择合适的语气回复。
    取值：EMOTION_NEUTRAL / EMOTION_ANXIOUS / EMOTION_ANGRY / EMOTION_DISAPPOINTED / EMOTION_URGENT。"""

    emotion_score: float
    """用户情绪评分（0.0~1.0）。用于触发转人工规则（>0.85 转人工）。"""

    customer_stage: str
    """客户所处阶段。帮助选择合适的话术。
    取值：STAGE_PRE_SALE / STAGE_IN_SALE / STAGE_AFTER_SALE / STAGE_UNKNOWN。"""

    # ========== D. 路由和执行字段 ==========
    selected_skill: Optional[str]
    """根据 intent 路由到的目标 skill 名称。LangGraph 根据此字段决定调用哪个 skill。"""

    skill_result: Optional[Dict[str, Any]]
    """Skill 执行后的返回数据。如退款结果、查询结果等。"""

    # ========== E. 业务规则字段 ==========
    policy_decision: Optional[str]
    """业务规则做出的决策。
    如退款 policy 输出："retention" / "refund_workflow" / "direct_refund_or_human_confirm"。
    State 只保存决策结果，不保存复杂规则本身。"""

    need_human: bool
    """是否需要转人工。True 时走转人工流程。"""

    human_reason: Optional[str]
    """转人工的原因。用于向用户和人工客服说明情况。"""

    # ========== F. 输出字段 ==========
    reply: Optional[str]
    """Agent 最终回复文本。"""

    # ========== G. 工程观测字段 ==========
    logs: List[Dict[str, Any]]
    """每步节点执行记录。包含节点名、输入摘要、输出摘要、耗时等。
    用于调试、测试和回放。"""

    errors: List[str]
    """节点执行失败和兜底信息。errors 不为空时会触发转人工。"""

    # ========== H. 多轮上下文字段（Phase 10.10） ==========
    conversation_history: List[Dict[str, str]]
    """最近几轮对话历史，由 Context Loader 在 graph 运行前注入。
       格式：[{"role": "user"/"assistant", "content": "..."}]
       用于 product_qa_skill 等节点处理追问。"""


def create_initial_state(
    session_id: str,
    user_message: str = "",
    image_url: Optional[str] = None,
    image_base64: Optional[str] = None,
) -> CustomerServiceState:
    """创建一个新的初始 State。

    所有字段设为默认值，logs 和 errors 每次创建新 list（不共用同一个列表）。

    Args:
        session_id: 会话唯一标识
        user_message: 用户输入文本
        image_url: 用户上传图片的 URL（可选）
        image_base64: 用户上传图片的 base64 编码（可选）

    Returns:
        填充了初始值的 CustomerServiceState
    """
    return {
        # A. 会话输入
        "session_id": session_id,
        "user_message": user_message,
        "image_url": image_url,
        "image_base64": image_base64,
        # B. 输入类型判断
        "modality": MODALITY_UNKNOWN,
        # C. 分析结果
        "text_analysis": None,
        "multimodal_analysis": None,
        "intent": None,
        "intent_confidence": 0.0,
        "emotion": EMOTION_NEUTRAL,
        "emotion_score": 0.0,
        "customer_stage": STAGE_UNKNOWN,
        # D. 路由和执行
        "selected_skill": None,
        "skill_result": None,
        # E. 业务规则
        "policy_decision": None,
        "need_human": False,
        "human_reason": None,
        # F. 输出
        "reply": None,
        # G. 工程观测
        "logs": [],
        "errors": [],
        # H. 多轮上下文
        "conversation_history": [],
    }
