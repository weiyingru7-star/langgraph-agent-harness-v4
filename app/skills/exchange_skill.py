"""
exchange_skill.py — 换货处理技能

职责：处理换货请求，记录换货信息。
"""


def run_exchange_skill(state: dict) -> dict:
    """执行换货处理。"""
    return {
        "skill_result": {
            "action": "exchange_flow",
            "message": "已进入换货流程",
            "next_step": "确认尺码/颜色/订单信息",
        }
    }
