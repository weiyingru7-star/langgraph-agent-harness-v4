"""FastAPI 接口测试（Phase 10.2）。"""

from fastapi.testclient import TestClient

from app.server import app

client = TestClient(app)


class TestHealth:
    """健康检查接口测试。"""

    def test_get_health_200(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_get_health_status(self):
        resp = client.get("/api/health")
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "v4-enhanced"
        assert data["tests_passed"] > 0


class TestChat:
    """聊天接口测试。"""

    def test_logistics_query(self):
        """纯文本物流问题。"""
        resp = client.post("/api/chat", json={
            "session_id": "test-api-001",
            "user_message": "我的快递怎么还没到",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"]
        assert data["intent"] == "logistics_question"
        assert data["selected_skill"] == "logistics_skill"

    def test_refund_query(self):
        """退款问题。"""
        resp = client.post("/api/chat", json={
            "session_id": "test-api-002",
            "user_message": "质量太差了我要退款",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "refund_request"
        assert data["policy_decision"] == "retention"
        assert data["need_human"] is True  # emotion 0.9 触发转人工

    def test_image_only(self):
        """纯图片问题。"""
        resp = client.post("/api/chat", json={
            "session_id": "test-api-003",
            "user_message": "",
            "image_url": "https://example.com/test.jpg",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["selected_skill"] is None

    def test_reply_not_empty(self):
        """响应中包含 reply。"""
        resp = client.post("/api/chat", json={
            "session_id": "test-api-004",
            "user_message": "你好",
        })
        data = resp.json()
        assert data["reply"]

    def test_response_contains_fields(self):
        """响应中包含关键分析字段。"""
        resp = client.post("/api/chat", json={
            "session_id": "test-api-005",
            "user_message": "你好",
        })
        data = resp.json()
        assert "intent" in data
        assert "emotion" in data
        assert "selected_skill" in data
        assert "need_human" in data

    def test_return_full_state(self):
        """return_full_state=true 时包含 state。"""
        resp = client.post("/api/chat", json={
            "session_id": "test-api-006",
            "user_message": "你好",
            "return_full_state": True,
        })
        data = resp.json()
        assert "state" in data
        assert data["state"]["reply"] == data["reply"]
