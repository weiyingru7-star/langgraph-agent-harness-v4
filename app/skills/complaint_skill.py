"""
complaint_skill.py — 投诉处理技能

职责：记录投诉信息，准备转人工。
"""


def run_complaint_skill(state: dict) -> dict:
    """记录投诉信息。"""
    return {
        "skill_result": {
            "action": "complaint_recorded",
            "message": "已记录投诉信息",
            "severity": "high",
        }
    }
