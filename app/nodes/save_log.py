"""
save_log.py — 日志保存节点

职责: 在流程结束前追加完成记录。
      检查 errors 中是否有错误信息。
      第一版不写外部日志文件。
"""

from datetime import datetime

from app.state.customer_state import CustomerServiceState


def save_log(state: CustomerServiceState) -> dict:
    """
    记录流程执行完成，检查是否有错误。

    读取字段: logs, errors
    写入字段: logs

    Args:
        state: 当前状态

    Returns:
        包含 logs 更新的部分 state dict
    """
    errors = state["errors"]
    error_info = f"，{len(errors)} 个错误" if errors else "，无错误"

    updated_logs = list(state["logs"])
    # 先追加本条日志再统计总数，使 node_count 包含 save_log 自身
    node_count = len(updated_logs) + 1

    updated_logs.append({
        "node": "save_log",
        "summary": f"流程执行完成，共 {node_count} 个节点{error_info}",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {"logs": updated_logs}
