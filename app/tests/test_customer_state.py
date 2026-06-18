"""create_initial_state() 和 CustomerServiceState 常量的测试。"""

from app.state.customer_state import (
    # modality constants
    MODALITY_IMAGE_ONLY,
    MODALITY_TEXT_ONLY,
    MODALITY_TEXT_WITH_IMAGE,
    MODALITY_UNKNOWN,
    # intent constants
    INTENT_COMPLAINT,
    INTENT_EXCHANGE_REQUEST,
    INTENT_HUMAN_REQUEST,
    INTENT_LOGISTICS_QUESTION,
    INTENT_PRODUCT_QUESTION,
    INTENT_RECOMMENDATION,
    INTENT_REFUND_REQUEST,
    INTENT_SMALLTALK,
    # emotion constants
    EMOTION_ANGRY,
    EMOTION_ANXIOUS,
    EMOTION_DISAPPOINTED,
    EMOTION_NEUTRAL,
    EMOTION_URGENT,
    # customer_stage constants
    STAGE_AFTER_SALE,
    STAGE_IN_SALE,
    STAGE_PRE_SALE,
    STAGE_UNKNOWN,
    # factory
    create_initial_state,
)


class TestCreateInitialState:
    """create_initial_state() 基础功能测试。"""

    def test_basic_initialization(self):
        """测试基础初始化：传入 session_id 和 user_message。"""
        state = create_initial_state(
            session_id="demo-session-001",
            user_message="我的快递怎么还没到",
        )

        # A. 会话输入
        assert state["session_id"] == "demo-session-001"
        assert state["user_message"] == "我的快递怎么还没到"
        assert state["image_url"] is None
        assert state["image_base64"] is None

        # B. 输入类型判断
        assert state["modality"] == "unknown"

        # C. 分析结果
        assert state["text_analysis"] is None
        assert state["multimodal_analysis"] is None
        assert state["intent"] is None
        assert state["intent_confidence"] == 0.0
        assert state["emotion"] == "neutral"
        assert state["emotion_score"] == 0.0
        assert state["customer_stage"] == "unknown"

        # D. 路由和执行
        assert state["selected_skill"] is None
        assert state["skill_result"] is None

        # E. 业务规则
        assert state["policy_decision"] is None
        assert state["need_human"] is False
        assert state["human_reason"] is None

        # F. 输出
        assert state["reply"] is None

        # G. 工程观测
        assert state["logs"] == []
        assert state["errors"] == []

    def test_image_url_initialization(self):
        """测试图片 URL 初始化。"""
        state = create_initial_state(
            session_id="demo-session-002",
            image_url="https://example.com/test.jpg",
        )

        assert state["session_id"] == "demo-session-002"
        assert state["user_message"] == ""
        assert state["image_url"] == "https://example.com/test.jpg"
        assert state["image_base64"] is None
        assert state["modality"] == "unknown"

    def test_logs_errors_not_shared(self):
        """测试 logs 和 errors 不是共享列表。

        每次调用 create_initial_state() 都应创建新的空列表，
        修改一个 state 不应影响另一个。
        """
        state1 = create_initial_state("s1")
        state2 = create_initial_state("s2")

        state1["logs"].append({"node": "test"})
        state1["errors"].append("test error")

        assert state2["logs"] == []
        assert state2["errors"] == []


class TestConstants:
    """枚举常量值正确性测试。"""

    def test_modality_constants(self):
        assert MODALITY_TEXT_ONLY == "text_only"
        assert MODALITY_IMAGE_ONLY == "image_only"
        assert MODALITY_TEXT_WITH_IMAGE == "text_with_image"
        assert MODALITY_UNKNOWN == "unknown"

    def test_intent_constants(self):
        assert INTENT_PRODUCT_QUESTION == "product_question"
        assert INTENT_RECOMMENDATION == "recommendation"
        assert INTENT_LOGISTICS_QUESTION == "logistics_question"
        assert INTENT_REFUND_REQUEST == "refund_request"
        assert INTENT_EXCHANGE_REQUEST == "exchange_request"
        assert INTENT_COMPLAINT == "complaint"
        assert INTENT_HUMAN_REQUEST == "human_request"
        assert INTENT_SMALLTALK == "smalltalk"

    def test_emotion_constants(self):
        assert EMOTION_NEUTRAL == "neutral"
        assert EMOTION_ANXIOUS == "anxious"
        assert EMOTION_ANGRY == "angry"
        assert EMOTION_DISAPPOINTED == "disappointed"
        assert EMOTION_URGENT == "urgent"

    def test_customer_stage_constants(self):
        assert STAGE_PRE_SALE == "pre_sale"
        assert STAGE_IN_SALE == "in_sale"
        assert STAGE_AFTER_SALE == "after_sale"
        assert STAGE_UNKNOWN == "unknown"
