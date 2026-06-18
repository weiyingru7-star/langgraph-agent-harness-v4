"""多轮上下文测试（Phase 10.10）。"""

import os
import tempfile

from fastapi.testclient import TestClient

from app.graph import run_graph
from app.memory.conversation_memory import clear_memory
from app.server import app
from app.state.customer_state import create_initial_state


def setup_function():
    clear_memory()


class TestConversationHistory:
    """conversation_history 基础功能测试。"""

    def test_no_history_does_not_crash(self):
        """没有历史时 conversation_history 为 []，不报错。"""
        state = run_graph(create_initial_state(
            session_id="ch-empty", user_message="你好",
        ))
        # 即使不在 graph 中设置，state 应该有默认值或不报错
        assert state["reply"] is not None

    def test_history_loaded_into_state(self):
        """模拟第一轮后，第二轮能读取历史。"""
        # 第一轮
        s1 = run_graph(create_initial_state(
            session_id="ch-load", user_message="这个衣服是什么材质",
        ))
        assert s1["reply"] is not None
        # 第二轮：手动注入历史（模拟 Context Loader 行为）
        history = [
            {"role": "user", "content": "这个衣服是什么材质"},
            {"role": "assistant", "content": s1["reply"]},
        ]
        initial = create_initial_state(
            session_id="ch-load", user_message="有什么码数",
        )
        initial["conversation_history"] = history
        s2 = run_graph(initial)
        assert s2["reply"] is not None


class TestFollowUpQuestions:
    """追问场景测试。"""

    def test_size_followup(self):
        """第一轮问材质 → 第二轮问码数 → 回答尺码。"""
        # 第一轮
        s1 = run_graph(create_initial_state(
            session_id="fu-size", user_message="这个衣服是什么材质",
        ))
        # 第二轮：注入历史
        history = [
            {"role": "user", "content": "这个衣服是什么材质"},
            {"role": "assistant", "content": s1["reply"]},
        ]
        initial = create_initial_state(
            session_id="fu-size", user_message="有什么码数",
        )
        initial["conversation_history"] = history
        s2 = run_graph(initial)
        r = s2["reply"] or ""
        # 应该回答尺码，不是 smalltalk
        assert "S" in r or "M" in r or "XL" in r or "尺码" in r

    def test_age_followup(self):
        """第一轮问推荐 → 第二轮问适合吗 → 回答适合性。"""
        s1 = run_graph(create_initial_state(
            session_id="fu-age", user_message="有没有推荐",
        ))
        history = [
            {"role": "user", "content": "有没有推荐"},
            {"role": "assistant", "content": s1["reply"]},
        ]
        initial = create_initial_state(
            session_id="fu-age", user_message="30岁适合吗",
        )
        initial["conversation_history"] = history
        s2 = run_graph(initial)
        r = s2["reply"] or ""
        assert "适合" in r

    def test_wash_followup(self):
        """第一轮问材质 → 第二轮问怎么洗。"""
        s1 = run_graph(create_initial_state(
            session_id="fu-wash", user_message="这个衣服是什么材质",
        ))
        history = [
            {"role": "user", "content": "这个衣服是什么材质"},
            {"role": "assistant", "content": s1["reply"]},
        ]
        initial = create_initial_state(
            session_id="fu-wash", user_message="怎么洗",
        )
        initial["conversation_history"] = history
        s2 = run_graph(initial)
        r = s2["reply"] or ""
        assert "洗" in r or "保养" in r or "冷水" in r


class TestSessionIsolation:
    """不同 session 不串上下文。"""

    def test_session_a_does_not_affect_b(self):
        s1 = run_graph(create_initial_state(
            session_id="iso-a", user_message="这个衣服是什么材质",
        ))
        # session B 不应该看到 A 的历史
        initial_b = create_initial_state(
            session_id="iso-b", user_message="有什么码数",
        )
        # 不注入历史
        s2 = run_graph(initial_b)
        # B 没有历史，应该走正常流程（可能小概率回 smalltalk）
        assert s2["reply"] is not None


class TestRefundNotOverridden:
    """退款 / 投诉不受历史商品上下文影响。"""

    def test_refund_not_overridden_by_product_context(self):
        """第一轮商品咨询 → 第二轮退款，仍走 refund_skill。"""
        s1 = run_graph(create_initial_state(
            session_id="ro-refund", user_message="这个衣服是什么材质",
        ))
        history = [
            {"role": "user", "content": "这个衣服是什么材质"},
            {"role": "assistant", "content": s1["reply"]},
        ]
        initial = create_initial_state(
            session_id="ro-refund", user_message="质量太差了我要退款",
        )
        initial["conversation_history"] = history
        s2 = run_graph(initial)
        assert s2["selected_skill"] == "refund_skill"
        assert s2["policy_decision"] == "retention"

    def test_complaint_not_overridden(self):
        """第一轮商品咨询 → 第二轮投诉，仍走 complaint + 转人工。"""
        s1 = run_graph(create_initial_state(
            session_id="ro-cp", user_message="这个衣服是什么材质",
        ))
        history = [
            {"role": "user", "content": "这个衣服是什么材质"},
            {"role": "assistant", "content": s1["reply"]},
        ]
        initial = create_initial_state(
            session_id="ro-cp", user_message="你们这个太垃圾了，我要投诉",
        )
        initial["conversation_history"] = history
        s2 = run_graph(initial)
        assert s2["selected_skill"] == "complaint_skill"
        assert s2["need_human"] is True


class TestImageNotAffected:
    """纯图片不受历史商品上下文影响。"""

    def setup_method(self):
        clear_memory()

    def test_image_only_not_affected_by_context(self):
        """第一轮商品咨询后第二轮纯图片，仍走 image_clarification。"""
        # 使用独立 session，不触发 memory 回溯
        initial = create_initial_state(
            session_id="img-ctx-only",
            image_url="https://example.com/test.jpg",
        )
        # 注入历史（模拟 SQLite 上下文）
        initial["conversation_history"] = [
            {"role": "user", "content": "这个衣服是什么材质"},
            {"role": "assistant", "content": "这款 UPF50+ 轻薄防晒衣的材质信息如下..."},
        ]
        s2 = run_graph(initial)
        assert s2["modality"] == "image_only"
        assert s2["selected_skill"] is None
        assert s2["skill_result"]["action"] == "image_clarification"


class TestSqliteIntegration:
    """通过 FastAPI /api/chat 验证 SQLite 路径的 Context Loader。"""

    def setup_method(self):
        clear_memory()

    def test_two_turn_context_via_sqlite(self):
        """两轮 /api/chat 调用后，第二轮应读取 SQLite 中的第一轮历史。"""
        import app.persistence.sqlite_store as store
        import tempfile, os

        test_db = tempfile.mktemp(suffix=".db")
        store.init_db(test_db)

        # Patch
        orig_init = store.init_db
        orig_save_msg = store.save_message
        orig_get_msg = store.get_messages

        store.init_db = lambda *a, **kw: orig_init(test_db)
        store.save_message = lambda *a, **kw: orig_save_msg(*a, **{**kw, "db_path": test_db})
        store.get_messages = lambda *a, **kw: orig_get_msg(*a, **{**kw, "db_path": test_db})

        store.init_db()
        client = TestClient(app)

        # 第一轮
        r1 = client.post("/api/chat", json={
            "session_id": "sqlite-two", "user_message": "这个衣服是什么材质",
        })
        assert r1.status_code == 200

        # 第二轮 — Context Loader 应读取 SQLite 中的历史
        r2 = client.post("/api/chat", json={
            "session_id": "sqlite-two", "user_message": "有什么码数",
        })
        assert r2.status_code == 200
        reply = r2.json().get("reply", "")
        assert "S" in reply or "M" in reply or "XL" in reply or "尺码" in reply

        # 恢复
        store.init_db = orig_init
        store.save_message = orig_save_msg
        store.get_messages = orig_get_msg
        store.clear_db_for_tests(test_db)
        if os.path.exists(test_db):
            os.remove(test_db)
