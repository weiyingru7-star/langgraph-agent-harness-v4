"""
sqlite_store.py — SQLite 持久化存储。

提供会话消息、Agent 运行记录、转人工记录的保存与查询。
第一版使用 Python 标准库 sqlite3，不引入 SQLAlchemy。

核心原则：
- 所有写入失败不应影响主业务逻辑（try/except 包裹）
- SQLite 只做持久化，不参与业务决策
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

_DEFAULT_DB = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "app.db"))

_SQL_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    image_url TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);

CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_message TEXT,
    image_url TEXT,
    modality TEXT,
    intent TEXT,
    emotion TEXT,
    emotion_score REAL,
    customer_stage TEXT,
    selected_skill TEXT,
    policy_decision TEXT,
    need_human INTEGER,
    human_reason TEXT,
    reply TEXT,
    logs_json TEXT,
    errors_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_session ON agent_runs(session_id, created_at);

CREATE TABLE IF NOT EXISTS human_handoffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    reason TEXT,
    intent TEXT,
    emotion TEXT,
    user_message TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL
);
"""


def _get_conn(db_path: str) -> sqlite3.Connection:
    """获取数据库连接。"""
    return sqlite3.connect(db_path)


def _now() -> str:
    """返回当前时间字符串。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
#  公开 API
# ============================================================

def init_db(db_path: str = _DEFAULT_DB) -> None:
    """
    初始化数据库，创建表结构。

    幂等操作——表已存在时不会重复创建。
    """
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = _get_conn(db_path)
        conn.executescript(_SQL_CREATE_TABLES)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[sqlite_store] 初始化数据库失败: {e}")


def save_message(
    session_id: str,
    role: str,
    content: str,
    image_url: Optional[str] = None,
    db_path: str = _DEFAULT_DB,
) -> None:
    """保存一条消息。"""
    try:
        conn = _get_conn(db_path)
        conn.execute(
            "INSERT INTO messages (session_id, role, content, image_url, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, image_url, _now()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[sqlite_store] 保存消息失败: {e}")


def save_agent_run(state: dict, db_path: str = _DEFAULT_DB) -> None:
    """保存 Agent 运行记录。"""
    try:
        logs_json = json.dumps(state.get("logs", []), ensure_ascii=False)
        errors_json = json.dumps(state.get("errors", []), ensure_ascii=False)

        conn = _get_conn(db_path)
        conn.execute(
            """INSERT INTO agent_runs
            (session_id, user_message, image_url, modality, intent, emotion,
             emotion_score, customer_stage, selected_skill, policy_decision,
             need_human, human_reason, reply, logs_json, errors_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                state.get("session_id"),
                state.get("user_message"),
                state.get("image_url"),
                state.get("modality"),
                state.get("intent"),
                state.get("emotion"),
                state.get("emotion_score"),
                state.get("customer_stage"),
                state.get("selected_skill"),
                state.get("policy_decision"),
                1 if state.get("need_human") else 0,
                state.get("human_reason"),
                state.get("reply"),
                logs_json,
                errors_json,
                _now(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[sqlite_store] 保存 agent_run 失败: {e}")


def save_handoff_if_needed(state: dict, db_path: str = _DEFAULT_DB) -> None:
    """如果 need_human=True，保存转人工记录。"""
    try:
        if not state.get("need_human"):
            return
        conn = _get_conn(db_path)
        conn.execute(
            "INSERT INTO human_handoffs (session_id, reason, intent, emotion, user_message, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                state.get("session_id"),
                state.get("human_reason"),
                state.get("intent"),
                state.get("emotion"),
                state.get("user_message"),
                "pending",
                _now(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[sqlite_store] 保存 handoff 失败: {e}")


def get_messages(session_id: str, limit: int = 20, db_path: str = _DEFAULT_DB) -> List[Dict[str, Any]]:
    """读取指定会话的消息（按时间正序）。"""
    try:
        conn = _get_conn(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY created_at ASC LIMIT ?",
            (session_id, limit),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[sqlite_store] 读取消息失败: {e}")
        return []


def get_agent_runs(session_id: str, limit: int = 20, db_path: str = _DEFAULT_DB) -> List[Dict[str, Any]]:
    """读取指定会话的 Agent 运行记录（按时间倒序，最新在前）。"""
    try:
        conn = _get_conn(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM agent_runs WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        )
        rows = []
        for row in cursor.fetchall():
            d = dict(row)
            # 还原 JSON 字段
            for field in ("logs_json", "errors_json"):
                if d.get(field) and isinstance(d[field], str):
                    d[field.replace("_json", "")] = json.loads(d[field])
                    del d[field]
            rows.append(d)
        conn.close()
        return rows
    except Exception as e:
        print(f"[sqlite_store] 读取 agent_runs 失败: {e}")
        return []


def clear_db_for_tests(db_path: str) -> None:
    """清空所有数据（仅用于测试）。"""
    try:
        conn = _get_conn(db_path)
        for table in ("messages", "agent_runs", "human_handoffs"):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[sqlite_store] 清空数据库失败: {e}")
