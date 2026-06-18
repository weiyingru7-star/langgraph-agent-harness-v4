"""SQLite 持久化测试（Phase 10.8）。"""

import json
import os
import tempfile

import pytest

# 使用临时数据库路径，不污染 data/app.db
TEST_DB = tempfile.mktemp(suffix=".db")


def setup_module():
    """测试前清理临时数据库。"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def teardown_module():
    """测试后清理临时数据库。"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestSqliteStore:
    """sqlite_store 基础功能测试。"""

    def test_init_db_creates_tables(self):
        from app.persistence.sqlite_store import init_db
        import sqlite3
        init_db(TEST_DB)
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert "messages" in tables
        assert "agent_runs" in tables
        assert "human_handoffs" in tables

    def test_save_user_message(self):
        from app.persistence.sqlite_store import save_message, get_messages
        save_message("s1", "user", "你好", db_path=TEST_DB)
        msgs = get_messages("s1", db_path=TEST_DB)
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "你好"

    def test_save_assistant_message(self):
        from app.persistence.sqlite_store import save_message, get_messages
        save_message("s2", "assistant", "您好，有什么可以帮您？", db_path=TEST_DB)
        msgs = get_messages("s2", db_path=TEST_DB)
        assert len(msgs) == 1
        assert msgs[0]["role"] == "assistant"

    def test_get_messages_limit(self):
        from app.persistence.sqlite_store import save_message, get_messages
        for i in range(5):
            save_message("s3", "user", f"msg{i}", db_path=TEST_DB)
        msgs = get_messages("s3", limit=3, db_path=TEST_DB)
        assert len(msgs) == 3

    def test_save_agent_run(self):
        from app.persistence.sqlite_store import save_agent_run, get_agent_runs
        state = {
            "session_id": "run1",
            "user_message": "质量太差了",
            "intent": "refund_request",
            "emotion": "angry",
            "emotion_score": 0.9,
            "customer_stage": "after_sale",
            "selected_skill": "refund_skill",
            "policy_decision": "retention",
            "need_human": True,
            "human_reason": "用户情绪评分过高",
            "reply": "非常抱歉…",
            "logs": [],
            "errors": [],
        }
        save_agent_run(state, db_path=TEST_DB)
        runs = get_agent_runs("run1", db_path=TEST_DB)
        assert len(runs) == 1
        assert runs[0]["intent"] == "refund_request"
        assert runs[0]["selected_skill"] == "refund_skill"
        assert runs[0]["need_human"] == 1  # SQLite stores bool as int

    def test_get_agent_runs(self):
        from app.persistence.sqlite_store import save_agent_run, get_agent_runs
        for i in range(3):
            state = {"session_id": "run2", "user_message": f"test{i}", "logs": [], "errors": []}
            save_agent_run(state, db_path=TEST_DB)
        runs = get_agent_runs("run2", db_path=TEST_DB)
        assert len(runs) == 3

    def test_save_handoff_when_needed(self):
        from app.persistence.sqlite_store import save_handoff_if_needed
        state = {
            "session_id": "ho1",
            "user_message": "我要投诉",
            "intent": "complaint",
            "emotion": "angry",
            "need_human": True,
            "human_reason": "投诉需要人工处理",
        }
        save_handoff_if_needed(state, db_path=TEST_DB)
        # Verify via raw SQL
        import sqlite3
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.execute("SELECT * FROM human_handoffs WHERE session_id='ho1'")
        rows = cursor.fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][2] == "投诉需要人工处理"  # reason column

    def test_no_handoff_when_not_needed(self):
        from app.persistence.sqlite_store import save_handoff_if_needed
        state = {"session_id": "ho2", "user_message": "你好", "need_human": False}
        save_handoff_if_needed(state, db_path=TEST_DB)
        import sqlite3
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.execute("SELECT COUNT(*) FROM human_handoffs WHERE session_id='ho2'")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 0

    def test_db_error_does_not_raise(self):
        from app.persistence.sqlite_store import save_message, save_agent_run
        bad_path = "/nonexistent/dir/test.db"
        # 不应抛出异常
        save_message("x", "user", "test", db_path=bad_path)
        save_agent_run({"session_id": "x", "logs": [], "errors": []}, db_path=bad_path)


class TestApiPersistence:
    """端到端测试：/api/chat 调用后产生持久化记录。"""

    def test_chat_creates_persistence(self):
        from app.persistence.sqlite_store import init_db
        init_db(TEST_DB)
        from fastapi.testclient import TestClient
        from app.server import app
        # Patch db_path for testing
        import app.persistence.sqlite_store as store
        original_init = store.init_db
        original_save_msg = store.save_message
        original_save_run = store.save_agent_run
        original_save_ho = store.save_handoff_if_needed

        def patched_init(*args, **kwargs):
            return original_init(TEST_DB)
        def patched_save_msg(*args, **kwargs):
            kwargs["db_path"] = TEST_DB
            return original_save_msg(*args, **kwargs)
        def patched_save_run(*args, **kwargs):
            kwargs["db_path"] = TEST_DB
            return original_save_run(*args, **kwargs)
        def patched_save_ho(*args, **kwargs):
            kwargs["db_path"] = TEST_DB
            return original_save_ho(*args, **kwargs)

        store.init_db = patched_init
        store.save_message = patched_save_msg
        store.save_agent_run = patched_save_run
        store.save_handoff_if_needed = patched_save_ho

        store.init_db()
        client = TestClient(app)
        resp = client.post("/api/chat", json={
            "session_id": "api-test-persist",
            "user_message": "我的快递怎么还没到",
        })
        assert resp.status_code == 200

        # 检查数据库中是否有记录
        import sqlite3
        conn = sqlite3.connect(TEST_DB)
        msg_count = conn.execute("SELECT COUNT(*) FROM messages WHERE session_id='api-test-persist'").fetchone()[0]
        run_count = conn.execute("SELECT COUNT(*) FROM agent_runs WHERE session_id='api-test-persist'").fetchone()[0]
        conn.close()
        assert msg_count >= 2  # user + assistant
        assert run_count >= 1

        # Restore
        store.init_db = original_init
        store.save_message = original_save_msg
        store.save_agent_run = original_save_run
        store.save_handoff_if_needed = original_save_ho
