"""本地知识库测试（Phase 10.6）。"""

import json

from app.graph import run_graph
from app.memory.conversation_memory import clear_memory
from app.state.customer_state import create_initial_state
from app.tools.local_faq_tool import query_faq
from app.tools.local_product_tool import query_product


def setup_function():
    clear_memory()


class TestDataFiles:
    """数据文件完整性测试。"""

    def test_products_json_exists(self):
        import os
        path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "products.json"))
        assert os.path.exists(path), "products.json 不存在"
        with open(path, "r", encoding="utf-8") as f:
            products = json.load(f)
        assert isinstance(products, list)
        assert len(products) >= 3

    def test_faq_json_exists(self):
        import os
        path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "faq.json"))
        assert os.path.exists(path), "faq.json 不存在"
        with open(path, "r", encoding="utf-8") as f:
            faqs = json.load(f)
        assert isinstance(faqs, list)
        assert len(faqs) >= 5


class TestLocalProductTool:
    """商品知识库工具测试。"""

    def test_query_product_match(self):
        result = query_product("这个衣服是什么材质")
        assert result["matched"] is True
        assert result["knowledge_source"] == "local_json"
        assert result["matched_product"] is not None

    def test_query_product_no_match(self):
        result = query_product("外星人电脑")
        assert result["matched"] is False
        assert result["knowledge_source"] == "local_json"

    def test_query_product_fallback_products(self):
        result = query_product("外星人电脑")
        assert "products" in result
        assert len(result["products"]) > 0


class TestLocalFaqTool:
    """FAQ 知识库工具测试。"""

    def test_query_faq_match_with_intent(self):
        result = query_faq("这个衣服什么尺码", "product_question")
        assert result["matched"] is True
        assert result["knowledge_source"] == "local_json"

    def test_query_faq_no_match(self):
        result = query_faq("xxxxxxxxxyyyyyy", None)
        assert result["matched"] is False

    def test_query_faq_match_any_intent(self):
        result = query_faq("怎么发货", None)
        assert result["matched"] is True


class TestSkillWithKnowledgeBase:
    """Skill 使用本地知识库的集成测试。"""

    def test_product_qa_uses_local_products(self):
        state = run_graph(create_initial_state(
            session_id="kb-mat", user_message="这个衣服是什么材质",
        ))
        assert state["intent"] == "product_question"
        assert state["selected_skill"] == "product_qa_skill"
        r = state["reply"] or ""
        assert "防晒衣" in r or "锦纶" in r
        for bad in ["运动鞋", "EVA", "鞋底", "39-44"]:
            assert bad not in r, f"含不当词：{bad}"

    def test_product_qa_size_query(self):
        state = run_graph(create_initial_state(
            session_id="kb-size", user_message="有什么码数",
        ))
        assert state["selected_skill"] == "product_qa_skill"
        r = state["reply"] or ""
        assert "S" in r or "M" in r or "XL" in r or "尺码" in r

    def test_product_qa_age_suit(self):
        state = run_graph(create_initial_state(
            session_id="kb-age", user_message="30岁适合吗",
        ))
        assert state["selected_skill"] == "product_qa_skill"
        r = state["reply"] or ""
        assert "适合" in r

    def test_recommendation_uses_local_products(self):
        state = run_graph(create_initial_state(
            session_id="kb-rec", user_message="有没有推荐",
        ))
        assert state["selected_skill"] == "recommendation_skill"
        r = state["reply"] or ""
        assert "运动鞋" not in r
        # 应该推荐 knowledge base 中的商品
        assert "防晒衣" in r or "外套" in r or "遮阳帽" in r

    def test_fallback_does_not_crash(self):
        state = run_graph(create_initial_state(
            session_id="kb-fb", user_message="xxxxxxxxxxxxxx",
        ))
        assert state["reply"] is not None
