"""通用 Product QA Resolver 测试（Phase 10.10.2）。

测试不依赖硬编码商品名，验证 resolver 能从 products.json 动态解析。
"""

from app.graph import run_graph
from app.memory.conversation_memory import clear_memory
from app.state.customer_state import create_initial_state
from app.tools.local_product_tool import resolve_product


def setup_function():
    clear_memory()


class TestGenericProductResolution:
    """通用商品解析测试（不依赖写死商品名）。"""

    def test_resolve_by_name(self):
        """按 name 匹配。"""
        r = resolve_product("UPF50+ 轻薄防晒衣多少钱")
        assert r["matched"] is True
        assert r["matched_product"]["product_id"] == "suncoat_001"

    def test_resolve_by_alias(self):
        """按 alias 匹配（动态从 products.json 读取）。"""
        r = resolve_product("运动外套有什么码数")
        assert r["matched"] is True
        assert r["matched_product"]["product_id"] == "jacket_002"

    def test_resolve_by_another_alias(self):
        """按不同 alias 匹配帽子。"""
        r = resolve_product("帽子多少钱")
        assert r["matched"] is True
        assert r["matched_product"]["product_id"] == "hat_003"

    def test_resolve_no_match(self):
        """无匹配时返回 matched=False。"""
        r = resolve_product("外星人电脑")
        assert r["matched"] is False


class TestProductSkillGeneric:
    """通用 Product QA Skill 全场景测试。"""

    def test_jacket_size(self):
        """"轻量运动外套有什么码数" → 尺码 M/L/XL/XXL。"""
        s = run_graph(create_initial_state(session_id="g-jack-size", user_message="轻量运动外套有什么码数"))
        r = s["reply"] or ""
        assert "M" in r and "XL" in r
        assert "UPF50+" not in r
        assert "防晒" not in r

    def test_jacket_material(self):
        """"运动外套是什么材质" → 材质信息（聚酯纤维）。"""
        s = run_graph(create_initial_state(session_id="g-jack-mat", user_message="运动外套是什么材质"))
        r = s["reply"] or ""
        assert "聚酯纤维" in r

    def test_hat_price(self):
        """"帽子多少钱" → 价格。"""
        s = run_graph(create_initial_state(session_id="g-hat-price", user_message="帽子多少钱"))
        r = s["reply"] or ""
        assert "49" in r or "89" in r or "元" in r

    def test_suncoat_suitability(self):
        """"防晒衣适合骑车吗" → 适合场景。"""
        s = run_graph(create_initial_state(session_id="g-sun-suit", user_message="防晒衣适合骑车吗"))
        r = s["reply"] or ""
        assert "骑车" in r or "适合" in r

    def test_jacket_care(self):
        """"运动外套怎么洗" → 保养信息。"""
        s = run_graph(create_initial_state(session_id="g-jack-care", user_message="运动外套怎么洗"))
        r = s["reply"] or ""
        assert "洗" in r or "机洗" in r

    def test_hat_color(self):
        """"遮阳帽有什么颜色" → 颜色信息。"""
        s = run_graph(create_initial_state(session_id="g-hat-color", user_message="遮阳帽有什么颜色"))
        r = s["reply"] or ""
        assert "米色" in r or "浅灰" in r or "藏青" in r or "颜色" in r

    def test_explicit_product_beats_history(self):
        """当前输入明确商品 > 历史上下文。"""
        history = [
            {"role": "user", "content": "这个衣服是什么材质"},
            {"role": "assistant", "content": "这款 UPF50+ 轻薄防晒衣的材质信息如下"},
        ]
        initial = create_initial_state(session_id="g-beat", user_message="运动外套有什么码数")
        initial["conversation_history"] = history
        s = run_graph(initial)
        r = s["reply"] or ""
        assert "M" in r and "XL" in r  # 运动外套尺码
        assert "S" not in r  # 不是防晒衣尺码

    def test_history_used_when_no_product(self):
        """无明确商品名时从历史推断商品。"""
        history = [
            {"role": "user", "content": "这个衣服是什么材质"},
            {"role": "assistant", "content": "这款 UPF50+ 轻薄防晒衣的材质信息如下"},
        ]
        initial = create_initial_state(session_id="g-hist", user_message="有什么码数")
        initial["conversation_history"] = history
        s = run_graph(initial)
        r = s["reply"] or ""
        assert "S" in r or "M" in r or "XL" in r  # 有尺码信息
        assert "尺码" in r or "码" in r

    def test_refund_still_priority(self):
        """"运动外套质量太差了我要退款" 仍走 refund_skill。"""
        s = run_graph(create_initial_state(session_id="g-refund", user_message="运动外套质量太差了我要退款"))
        assert s["selected_skill"] == "refund_skill"
        assert s["policy_decision"] == "retention"

    def test_no_product_clarifies(self):
        """"30岁适合吗" 无商品名时澄清。"""
        s = run_graph(create_initial_state(session_id="g-clarify", user_message="30岁适合吗"))
        r = s["reply"] or ""
        assert "哪款商品" in r or "商品名称" in r or "型号" in r


class TestHypotheticalProduct:
    """模拟替换知识库后的通用性测试。"""

    def test_hypothetical_backpack(self):
        """用临时商品验证 resolver 不依赖写死商品名。"""
        import json, os
        from app.tools.local_product_tool import resolve_product

        # 备份原数据
        orig_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "products.json"))
        backup = open(orig_path, "r", encoding="utf-8").read()

        # 替换为测试商品（结构一致但内容不同）
        test_products = [
            {
                "product_id": "bag_999",
                "name": "轻量运动背包",
                "aliases": ["背包", "双肩包", "运动背包"],
                "category": "背包",
                "price_range": "199-299 元",
                "material": "尼龙防泼水面料",
                "sizes": ["20L", "30L", "40L"],
                "colors": ["黑色", "灰色"],
                "features": ["防水", "轻量", "多隔层"],
                "suitable_scenarios": ["徒步", "旅行", "通勤"],
                "care_instructions": "湿布擦拭即可"
            }
        ]
        with open(orig_path, "w", encoding="utf-8") as f:
            json.dump(test_products, f, ensure_ascii=False, indent=2)

        # 测试新商品能否被正确识别
        try:
            r_size = resolve_product("背包多大")
            assert r_size["matched"] is True, f"背包未匹配: {r_size}"
            assert r_size["matched_product"]["product_id"] == "bag_999"
            assert "20L" in str(r_size["matched_product"]["sizes"])

            r_price = resolve_product("双肩包多少钱")
            assert r_price["matched"] is True
            assert "199" in r_price["matched_product"]["price_range"]

            # 测试带新商品的完整对话
            s = run_graph(create_initial_state(session_id="g-backpack", user_message="轻量运动背包有什么码数"))
            r = s["reply"] or ""
            assert "20L" in r or "30L" in r
            assert "防晒衣" not in r  # 不应回退到旧商品
        finally:
            # 恢复原数据
            with open(orig_path, "w", encoding="utf-8") as f:
                f.write(backup)
