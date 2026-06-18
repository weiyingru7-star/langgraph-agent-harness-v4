"""
recommendation_skill.py — 商品推荐技能

职责：根据用户需求做售前推荐。
      第一版没有真实商品库，返回保守推荐说明。
"""


def run_recommendation_skill(state: dict) -> dict:
    """执行商品推荐，返回推荐信息。

    Phase 10 说明：当前为 Demo 阶段，暂未接入真实商品知识库。
    返回保守推荐建议，不编造具体商品。
    """
    return {
        "skill_result": {
            "action": "recommendation_demo",
            "message": (
                "我可以帮您推荐。当前 Demo 暂未接入真实商品库，"
                "我先根据常见需求给您一个保守建议：如果是夏季通勤/"
                "骑车，可以优先考虑轻薄透气、防晒等级 UPF50+ 的防晒衣；"
                "如果是运动场景，可以选择轻量运动外套。"
                "您也可以补充预算、尺码和使用场景，我再进一步推荐。"
            ),
            "note": "Demo mock 数据，后续接入本地商品知识库",
        }
    }
