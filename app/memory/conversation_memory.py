"""
conversation_memory.py — 简易会话记忆

职责：保存每个 session 最近一轮 user_message。
      第一版用内存 dict，不接数据库。
"""

_store: dict[str, str] = {}


def save_last_user_message(session_id: str, user_message: str) -> None:
    """保存最近一轮 user_message。空消息不覆盖已有记忆。"""
    if user_message:
        _store[session_id] = user_message


def get_last_user_message(session_id: str) -> str | None:
    """读取最近一轮 user_message。"""
    return _store.get(session_id)


def clear_memory() -> None:
    """清理所有记忆（用于测试隔离）。"""
    _store.clear()
