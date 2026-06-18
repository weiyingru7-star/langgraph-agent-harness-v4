# 本地知识库设计 — LOCAL_KNOWLEDGE_BASE_DESIGN

> **Phase 10.5 · 设计文档**
> 目标：把硬编码 mock 数据升级为本地数据驱动的知识库。

---

## 一、为什么要加本地知识库

### 当前短板

| 问题 | 现状 | 影响 |
|------|------|------|
| 商品数据硬编码 | `mock_product_tool.py` 写死一套数据 | 换商品必须改代码，不是数据驱动 |
| 问答与商品脱节 | `product_qa_skill` 只返回固定字段 | 用户问码数/年龄/材质拿不到针对性答案 |
| FAQ 写在代码里 | 没有独立 FAQ 文件 | 售后规则修改必须改代码 |
| 不适合作品集展示 | "数据从 JSON 读取" 比 "写在代码里" 更专业 | 面试官看重数据与逻辑分离 |

### 增强价值

```
之前：mock_product_tool → 硬编码返回同一双数据
之后：data/products.json → local_product_tool → 按需查询

面试官看到的区别：
  "您的商品数据来自哪里？" ← 一定会问
  → "来自 data/products.json，后续可以切换到 Dify 或数据库"
  ✅ 比 "写在 Python 文件里" 好很多
```

---

## 二、数据目录设计

```
data/
├── products.json          # 商品资料库
├── faq.json               # 常见问答库
└── refund_policy.md       # 退款政策说明
```

---

## 三、products.json 设计

至少 3 个商品，覆盖服饰/防晒/配件品类。

```json
[
  {
    "product_id": "suncoat_001",
    "name": "UPF50+ 轻薄防晒衣",
    "category": "防晒服",
    "material": "锦纶混纺面料，轻薄透气",
    "features": ["UPF50+ 防晒", "轻薄", "透气", "适合夏季通勤"],
    "suitable_scene": ["骑车", "通勤", "户外", "旅行"],
    "suitable_people": "适合 20-45 岁日常通勤、户外防晒、骑车和旅行穿着，版型基础，不挑年龄。",
    "sizes": ["S", "M", "L", "XL"],
    "price_range": "129-199 元",
    "care_instructions": "建议冷水手洗，避免高温烘干"
  },
  {
    "product_id": "jacket_002",
    "name": "轻量运动外套",
    "category": "外套",
    "material": "聚酯纤维 + 弹性面料，防泼水处理",
    "features": ["防风", "防泼水", "轻量", "弹性好"],
    "suitable_scene": ["跑步", "骑行", "户外", "健身"],
    "suitable_people": "适合运动爱好者日常训练和户外活动穿着。",
    "sizes": ["M", "L", "XL", "XXL"],
    "price_range": "249-399 元",
    "care_instructions": "建议冷水轻柔机洗，不可漂白"
  },
  {
    "product_id": "hat_003",
    "name": "可折叠遮阳帽",
    "category": "配件",
    "material": "速干面料 + 可调节帽围",
    "features": ["UPF50+ 防晒", "可折叠", "速干", "轻便"],
    "suitable_scene": ["旅行", "户外", "通勤", "徒步"],
    "suitable_people": "适合所有户外场景，折叠后方便随身携带。",
    "sizes": ["均码（可调节）"],
    "price_range": "49-89 元",
    "care_instructions": "手洗或轻柔机洗，自然晾干"
  }
]
```

### 字段说明

| 字段 | 说明 | 用于回答 |
|------|------|---------|
| `product_id` | 商品唯一 ID | — |
| `name` | 商品名称 | 商品名称回答 |
| `category` | 品类 | 分类筛选 |
| `material` | 材质说明 | 材质/面料问答 |
| `features` | 特性列表 | "有什么特点"问答 |
| `suitable_scene` | 适用场景 | "适合什么场景"问答 |
| `suitable_people` | 适合人群 | "适合我吗"/年龄问答 |
| `sizes` | 尺码 | 尺码问答 |
| `price_range` | 价格区间 | 价格问答 |
| `care_instructions` | 保养说明 | 清洗/保养问答 |

---

## 四、faq.json 设计

```json
[
  {
    "faq_id": "faq_001",
    "question_keywords": ["材质", "面料", "透气", "防晒"],
    "answer": "商品采用锦纶混纺面料，轻薄透气，UPF50+ 防晒指数，适合夏季日常使用。",
    "related_intents": ["product_question", "recommendation"]
  },
  {
    "faq_id": "faq_002",
    "question_keywords": ["尺码", "码数", "大小", "能穿"],
    "answer": "防晒衣尺码为 S/M/L/XL，运动外套为 M/L/XL/XXL，遮阳帽为均码可调节。建议按平时尺码选购，如果拿不准可以告诉我身高体重帮您参考。",
    "related_intents": ["product_question"]
  },
  {
    "faq_id": "faq_003",
    "question_keywords": ["发货", "什么时候发", "多久发"],
    "answer": "现货商品 48 小时内发货，预售商品以页面标注为准。发货后会通过短信通知物流单号。",
    "related_intents": ["logistics_question"]
  },
  {
    "faq_id": "faq_004",
    "question_keywords": ["退换货", "退货", "换货", "退"],
    "answer": "商品不影响二次销售的情况下，签收后 7 天内可申请退换货。具体退换流程可以联系客服处理。",
    "related_intents": ["refund_request", "exchange_request"]
  },
  {
    "faq_id": "faq_005",
    "question_keywords": ["怎么洗", "保养", "清洗", "洗涤"],
    "answer": "建议冷水轻柔手洗或使用洗衣袋机洗，不可漂白、不可高温烘干，自然晾干即可保持最佳状态。",
    "related_intents": ["product_question"]
  },
  {
    "faq_id": "faq_006",
    "question_keywords": ["推荐", "买哪款", "哪个好", "适合我吗"],
    "answer": "夏季推荐防晒衣（UPF50+ 轻薄透气），运动推荐轻量外套（防风防泼水），旅行推荐遮阳帽（可折叠便携）。具体可以告诉我使用场景帮您推荐。",
    "related_intents": ["recommendation", "product_question"]
  },
  {
    "faq_id": "faq_007",
    "question_keywords": ["物流", "快递", "什么时候到", "到哪了"],
    "answer": "快递发出后通常在 3-5 个工作日内到达，具体时效因地区而异。您可以提供订单号帮您查询具体物流信息。",
    "related_intents": ["logistics_question"]
  }
]
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `faq_id` | FAQ 唯一 ID |
| `question_keywords` | 触发关键词列表 |
| `answer` | 标准回答 |
| `related_intents` | 关联的 intent，用于路由时选择 |

---

## 五、refund_policy.md 设计

```markdown
# 退款政策

## 首次退款请求

- 优先安抚用户情绪，确认问题原因。
- 了解用户诉求后，尝试补偿方案（换货、部分退款、优惠券等）。
- 不主动承诺全额退款。
- 如果用户坚持，记录诉求并交给人工客服确认。

## 第二次明确退款请求

- 进入退款流程。
- 由运营人员核实订单状态和商品问题。
- 核实后执行退款操作（原路返回，3-5 个工作日到账）。

## 多次投诉或强烈情绪

- 情绪评分 > 0.85 时触发转人工。
- 人工客服优先处理。
- 不绕过人工审核。

## 重要安全规则

- 系统不自动执行退款操作。
- 所有退款必须经由人工客服确认。
- 退款决策规则由 refund_policy.py 控制，不来自此文档。
```

### 用途说明

```
Markdown 文件 = 人工客服参考材料，不是自动规则来源。
Agent 可以读取此文件作为回复参考，
但最终退款决策仍由 refund_policy.py 控制。
```

---

## 六、新增 Tool 设计

### local_product_tool

```python
# app/tools/local_product_tool.py

def query_product(user_message: str) -> dict:
    """
    从 data/products.json 查询匹配的商品。

    匹配方式：关键词简单匹配（第一版不做 embedding）。
    返回：匹配到的商品 dict，或 no_match 标志。
    """
```

**匹配逻辑（伪代码）：**

```python
def query_product(user_message: str) -> dict:
    products = _load_products()
    text = user_message.lower()

    # 关键词匹配优先级：品类 > 特性 > 场景
    for keyword, product_id in CATEGORY_KEYWORDS:
        if keyword in text:
            return match_by_id(product_id)

    if no_match:
        return {"match": False, "fallback": True, "products": products[:2]}
```

### local_faq_tool

```python
# app/tools/local_faq_tool.py

def query_faq(user_message: str, intent: str) -> dict:
    """
    从 data/faq.json 查询匹配的 FAQ。

    匹配方式：遍历 question_keywords 做包含匹配。
    返回：匹配到的 FAQ dict，或 no_match 标志。
    """
```

**匹配逻辑（伪代码）：**

```python
def query_faq(user_message: str, intent: str) -> dict:
    faqs = _load_faqs()
    text = user_message.lower()

    # 优先匹配 intent，再匹配关键词
    for faq in faqs:
        if intent in faq.get("related_intents", []):
            if any(kw in text for kw in faq["question_keywords"]):
                return {"match": True, "faq": faq["answer"]}

    return {"match": False}
```

### 为什么不做 embedding

```
✅ 当前做法：关键词包含匹配
   - 简单、可预测、零依赖
   - 适用于有限数量的商品和 FAQ

❌ 暂不做 embedding / 向量检索
   - 需要 embedding 模型依赖
   - 小数据集下关键词匹配已经够用
   - 后续可以升级到 Dify / RAG

什么时候升级：
   当数据量超过 50 条时，考虑 embedding
   当前 3 商品 + 7 FAQ，不需要
```

---

## 七、Skill 调整设计

### product_qa_skill

```
当前：
  get_mock_product_info() → 固定返回防晒衣

调整后：
  local_faq_tool → 优先查 FAQ
  local_product_tool → 再查商品
  都无匹配 → 回退当前 mock 商品资料
```

```python
def run_product_qa_skill(state: dict) -> dict:
    text = state.get("user_message", "") or ""

    # 1. 查 FAQ
    faq = local_faq_tool.query_faq(text, "product_question")
    if faq["match"]:
        return {"skill_result": {"action": "product_answer", "message": faq["faq"]}}

    # 2. 查商品
    product = local_product_tool.query_product(text)
    if product.get("match"):
        return {"skill_result": {"action": "product_answer", "product_info": product, "message": _build_reply(product)}}

    # 3. 回退 mock
    return mock_product_reply()
```

### recommendation_skill

```
当前：
  返回保守说明，无具体商品。

调整后：
  local_product_tool → 读取 products.json
  返回 2-3 个推荐商品（含名称/材质/价格/场景）
  仍然保留说明：当前为示例数据。
```

### refund_skill

```
refund_policy.md 可以读取作为参考材料，
但最终退款决策仍由 refund_policy.py 控制。
Skill 不因读取 Markdown 而绕开 Policy。
```

### 禁止的修改

```
❌ refund_skill 不因读取 refund_policy.md 就自行决定退款
❌ 不把退款规则写进 prompt
❌ 不让 LLM 根据 Markdown 做退款决策
❌ 不删除 refund_policy.py
```

---

## 八、测试设计

新增 `tests/test_local_knowledge_base.py`：

| # | 测试 | 断言 |
|---|------|------|
| 1 | products.json 存在且可读取 | 文件存在，JSON 有效 |
| 2 | products.json 至少含 3 个商品 | `len(products) >= 3` |
| 3 | faq.json 存在且可读取 | 文件存在，JSON 有效 |
| 4 | faq.json 至少含 5 条 FAQ | `len(faqs) >= 5` |
| 5 | local_product_tool 能匹配商品 | 输入"防晒衣"返回 match=True |
| 6 | local_product_tool 无匹配时返回 fallback | 输入"外星人"返回 match=False |
| 7 | local_faq_tool 能匹配 FAQ | 输入"尺码"返回 match=True |
| 8 | local_faq_tool 无匹配时返回 fallback | 输入"xxx"返回 match=False |
| 9 | 原有 pytest 全部通过 | `pytest -q` 无失败 |

---

## 九、Streamlit 展示增强

在右侧 Agent 分析面板增加：

```
📂 数据来源
- product: local_products.json
- faq: local_faq.json
```

但不要在 Streamlit 里写检索逻辑。数据来源信息由后端通过 API 返回。

---

## 十、禁止事项

| 禁止 | 原因 |
|------|------|
| 不接 Dify | 增加部署成本，当前不需要 |
| 不接数据库 | SQLite 增加复杂度，当前 JSON 够用 |
| 不接向量库 | 数据集小，关键词匹配够用 |
| 不接真实电商 API | 需要商家授权 |
| 不接真实退款 API | 安全风险 |
| 不改 Agent 核心流程 | graph.py / policies 保持不变 |
| 不让 LLM 决定退款 | Policy 仍然控制 |
| 不删除已有测试 | 保持回归覆盖 |

---

## 十一、Phase 10.6 实现边界

### 允许新增/修改

| 文件 | 操作 |
|------|------|
| `data/products.json` | **新建** |
| `data/faq.json` | **新建** |
| `data/refund_policy.md` | **新建** |
| `app/tools/local_product_tool.py` | **新建** |
| `app/tools/local_faq_tool.py` | **新建** |
| `app/skills/product_qa_skill.py` | **修改** — 优先查本地知识库 |
| `app/skills/recommendation_skill.py` | **修改** — 读取商品列表 |
| `app/tests/test_local_knowledge_base.py` | **新建** |
| `README.md` | 少量补充运行说明 |

### 不得修改

| 文件 | 原因 |
|------|------|
| `app/state/customer_state.py` | 核心结构不变 |
| `app/graph.py` | 主流程不变 |
| `app/policies/refund_policy.py` | 退款规则不变 |
| `app/api/` | 核心逻辑不变 |
| `app/web/` | 不写检索逻辑 |
| 现有 tests | 不删除、不降低覆盖 |

---

## 十二、验收标准

| # | 验收项 | 验证方式 |
|---|--------|---------|
| 1 | `.venv/bin/python -m pytest` 全部通过 | 运行测试 |
| 2 | `.venv/bin/python -m app.main` CLI 可用 | 运行 |
| 3 | `uvicorn app.server:app` FastAPI 可用 | 启动 + curl |
| 4 | Streamlit 页面可用 | 启动 |
| 5 | "这件衣服是什么材质" → 使用 products.json 回复 | end-to-end 测试 |
| 6 | "怎么洗" → 使用 faq.json 回复 | end-to-end 测试 |
| 7 | 无匹配输入 → fallback（不崩溃） | end-to-end 测试 |
| 8 | 退款决策仍由 refund_policy.py 控制 | 代码审查 |
| 9 | 没有接 Dify / 数据库 / 向量库 | 代码审查 |

---

> **下一阶段建议：** 进入 **Phase 10.6**，根据本文档实现本地知识库。
