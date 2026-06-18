"""
conversation_memory.py — 会话记忆管理

职责: 管理对话上下文的保存、读取和清理。
      第一版使用内存存储，后续可替换为数据库。
"""

from typing import Dict, List, Optional


class ConversationMemory:
    """
    会话记忆管理器。

    负责:
    1. 保存每轮对话的完整状态
    2. 根据 session_id 读取历史
    3. 提供会话摘要功能
    """

    def __init__(self):
        """初始化记忆存储（当前使用内存）。"""
        self._sessions: Dict[str, List[dict]] = {}

    def save(self, session_id: str, state: dict) -> None:
        """
        保存一轮对话状态到指定会话。

        Args:
            session_id: 会话 ID
            state: 当前状态字典
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append(state)

    def get_history(self, session_id: str) -> List[dict]:
        """
        获取指定会话的历史记录。

        Args:
            session_id: 会话 ID

        Returns:
            历史状态列表
        """
        return self._sessions.get(session_id, [])

    def clear(self, session_id: str) -> None:
        """
        清除指定会话的记忆。

        Args:
            session_id: 会话 ID
        """
        self._sessions.pop(session_id, None)
