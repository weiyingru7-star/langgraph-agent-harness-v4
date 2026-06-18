from .customer_state import (
    # 枚举常量 - modality
    MODALITY_TEXT_ONLY,
    MODALITY_IMAGE_ONLY,
    MODALITY_TEXT_WITH_IMAGE,
    MODALITY_UNKNOWN,
    # 枚举常量 - intent
    INTENT_PRODUCT_QUESTION,
    INTENT_RECOMMENDATION,
    INTENT_LOGISTICS_QUESTION,
    INTENT_REFUND_REQUEST,
    INTENT_EXCHANGE_REQUEST,
    INTENT_COMPLAINT,
    INTENT_HUMAN_REQUEST,
    INTENT_SMALLTALK,
    # 枚举常量 - emotion
    EMOTION_NEUTRAL,
    EMOTION_ANXIOUS,
    EMOTION_ANGRY,
    EMOTION_DISAPPOINTED,
    EMOTION_URGENT,
    # 枚举常量 - customer_stage
    STAGE_PRE_SALE,
    STAGE_IN_SALE,
    STAGE_AFTER_SALE,
    STAGE_UNKNOWN,
    # 类型
    CustomerServiceState,
    # 工厂函数
    create_initial_state,
)

__all__ = [
    # modality
    "MODALITY_TEXT_ONLY",
    "MODALITY_IMAGE_ONLY",
    "MODALITY_TEXT_WITH_IMAGE",
    "MODALITY_UNKNOWN",
    # intent
    "INTENT_PRODUCT_QUESTION",
    "INTENT_RECOMMENDATION",
    "INTENT_LOGISTICS_QUESTION",
    "INTENT_REFUND_REQUEST",
    "INTENT_EXCHANGE_REQUEST",
    "INTENT_COMPLAINT",
    "INTENT_HUMAN_REQUEST",
    "INTENT_SMALLTALK",
    # emotion
    "EMOTION_NEUTRAL",
    "EMOTION_ANXIOUS",
    "EMOTION_ANGRY",
    "EMOTION_DISAPPOINTED",
    "EMOTION_URGENT",
    # customer_stage
    "STAGE_PRE_SALE",
    "STAGE_IN_SALE",
    "STAGE_AFTER_SALE",
    "STAGE_UNKNOWN",
    # 类型和工厂
    "CustomerServiceState",
    "create_initial_state",
]
