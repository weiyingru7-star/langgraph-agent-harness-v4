"""
human_skill.py — 人工处理技能

职责：处理用户明确要求人工的情况，准备转人工。
"""


def run_human_skill(state: dict) -> dict:
    """准备转人工处理。"""
    return {
        "skill_result": {
            "action": "human_transfer",
            "message": "用户明确要求人工，准备转人工处理",
        }
    }
