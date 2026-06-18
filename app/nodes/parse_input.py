"""
parse_input.py — 输入解析节点

职责: 接收初始 state，不做业务判断，记录输入摘要到 logs。
"""

from datetime import datetime

from app.state.customer_state import CustomerServiceState


def parse_input(state: CustomerServiceState) -> dict:
    """
    接收用户输入，记录执行日志。

    读取字段: session_id, user_message, image_url, image_base64
    写入字段: logs

    Args:
        state: 当前状态

    Returns:
        包含 logs 更新的部分 state dict
    """
    # 构造日志摘要
    has_image = "有" if state["image_url"] or state["image_base64"] else "无"
    summary = (
        f"会话 {state['session_id']}："
        f"收到用户输入：{state['user_message'] or '（空）'}，图片：{has_image}"
    )

    # 读取已有 logs，追加新条目
    updated_logs = list(state["logs"])
    updated_logs.append({
        "node": "parse_input",
        "summary": summary,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {"logs": updated_logs}
