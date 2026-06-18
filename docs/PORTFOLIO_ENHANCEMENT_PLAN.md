# 作品集增强计划 — PORTFOLIO_ENHANCEMENT_PLAN

> **Phase 10 · 设计文档**
> 目标：把 CLI + Mock Agent Harness 学习项目，升级为更完整的 AI 应用作品集项目。

---

## 一、当前作品集的短板

### 现状分析

| 维度 | 当前 V4-lite | 作品集需要的 |
|------|-------------|-------------|
| 交互方式 | CLI 命令行 | Web 页面 / API |
| 数据展示 | JSON 打印 | 可视化 trace + 聊天 UI |
| 数据来源 | mock_tool 硬编码 | 本地知识库文件 |
| 持久化 | 内存 dict | SQLite 可查 |
| AI 能力 | 关键词 + 模板 | LLM 增强但不失控制 |
| 项目复杂度 | 纯后端工程 | 全栈 AI 应用 |

### 5 个短板

1. **别人没法试用** — 必须跑 CLI，看不到界面
2. **数据都是 mock 硬编码** — skill_result 永远一样
3. **没有持久化** — 关了终端什么都没了
4. **没有 AI 感觉** — 关键词 + 模板显得"很规则"
5. **看不到流程** — JSON 输出不直观

### 这 5 个增强模块解决什么

| 模块 | 解决短板 |
|------|---------|
| FastAPI 接口 | 别人可以用 curl / 前端调你的服务 |
| Web Demo 页面 | 打开浏览器就能试用，展示效果直观 |
| 本地知识库 | mock 数据从 JSON 文件读取，可维护 |
| SQLite 会话 | 关掉重启还能看到历史对话 |
| LLM 润色回复 | 回复更自然，但仍然受 Policy 控制 |

---

## 二、为什么不能推翻当前架构

```
┌──────────────────────────────────────────┐
│  当前 V4-lite 核心价值                    │
│                                          │
│  ✅ State 设计清晰                       │
│  ✅ LangGraph 节点完整                   │
│  ✅ Skill/Tool/Policy 分层               │
│  ✅ Logs/Errors 可观测                   │
│  ✅ 60 个 pytest                         │
│  ✅ 7 份设计文档                         │
└──────────────────────────────────────────┘
```

增强模块**叠加在现有架构之上**，不修改核心：

```
增强层（新增）：
  FastAPI → 对外暴露接口
  Web UI  → 可视化聊天
  Knowledge Base → 替换 mock 数据源
  SQLite  → 保存 run 记录
  LLM     → 替换关键词 + 模板（保留 Policy 控制）

核心层（不变）：
  CustomerServiceState
  LangGraph Nodes
  Skills / Tools / Policies
  Logs / Tests
```

---

## 三、模块 1：FastAPI 接口层

### 解决什么短板

- **之前：** 别人要看效果必须先 clone、装 venv、跑 CLI
- **之后：** 别人可以通过 HTTP 调用，curl / Postman / 前端都能接

### 技术栈

```
FastAPI + uvicorn
```

### 目录位置

```
app/api/
├── __init__.py
├── server.py        # FastAPI 应用 + 路由
└── schemas.py       # Pydantic 请求/响应模型
```

### API 设计

**POST /api/chat**

请求：
```json
{
  "session_id": "uuid-or-null",
  "user_message": "我的快递怎么还没到",
  "image_url": null,
  "image_base64": null
}
```

响应：
```json
{
  "session_id": "uuid-xxx",
  "reply": "感谢您的耐心等待……",
  "intent": "logistics_question",
  "intent_confidence": 0.8,
  "emotion": "anxious",
  "emotion_score": 0.65,
  "customer_stage": "in_sale",
  "selected_skill": "logistics_skill",
  "policy_decision": null,
  "need_human": false,
  "human_reason": null,
  "logs": [...]
}
```

**GET /api/health**

```json
{
  "status": "ok",
  "version": "v4-enhanced",
  "tests_passed": 60
}
```

### 设计原则

```
FastAPI 是薄层，不包含业务逻辑
  ✓ 接收请求 → 调用 run_graph → 返回结果
  ✗ 不做分类、不做路由、不做决策
```

---

## 四、模块 2：Web Demo 页面

### 解决什么短板

- **之前：** 面试官看 README 上的 JSON 截图
- **之后：** 面试官打开链接就能打字聊天

### 技术栈

```
方案 A：Streamlit（推荐，最快）
  优点：纯 Python，一行 streamlit run，不需要前端知识
  缺点：自定义 UI 有限

方案 B：简单 HTML + JS（更灵活）
  优点：可以精细控制 UI、打字机效果、移动端适配
  缺点：需要写 HTML/CSS/JS
```

**建议：先用 Streamlit 快速出效果，后续可以升级为 HTML。**

### Streamlit 方案（推荐）

```
app/web/
├── st_app.py            # Streamlit 应用
```

**页面布局：**

```
┌──────────────────────────────────────────────┐
│  LangGraph 客服 Agent Demo                    │
├──────────────────────────────────────────────┤
│  [输入框: 请输入您的问题              ] [发送] │
│  [图片 URL 输入框（可选）           ]        │
├──────────────────────────────────────────────┤
│  AI: 感谢您的耐心等待……                      │
│  ──────────────────────────────────────       │
│  意图: logistics_question                     │
│  情绪: anxious (0.65)                         │
│  技能: logistics_skill                        │
│  转人工: 否                                   │
│  ──────────────────────────────────────       │
│  🡒 parse_input ✓                             │
│  🡒 decide_modality ✓                         │
│  🡒 classify_intent ✓                         │
│  🡒 route_to_skill ✓                          │
│  🡒 generate_reply ✓                          │
└──────────────────────────────────────────────┘
```

**Streamlit 的好处：**
- 不用学 React/Vue
- 不用配前后端联调
- 一行 `streamlit run app/web/st_app.py` 就能跑
- 聊天记录自动保持
- 面试官不会在意你用 Streamlit 还是 React

### 用户能直观看到的东西

| 展示项 | 说明 |
|--------|------|
| 聊天对话 | 用户输入 + AI 回复 |
| intent / emotion | 展示 Agent "理解"了用户 |
| selected_skill | 展示 Agent "选择"了能力 |
| logs trace | 展示 11 个节点的执行过程 |
| need_human | 展示 Policy 生效 |

---

## 五、模块 3：本地商品/FAQ 知识库

### 解决什么短板

- **之前：** `mock_product_tool` 永远返回同一双鞋
- **之后：** 数据从 JSON 文件读取，可以扩展、维护、展示数据驱动

### 目录位置

```
data/
├── products.json          # 商品库
├── faq.json               # 常见问答
└── refund_policy.md       # 退款政策文档
```

### 示例数据结构

**products.json**

```json
[
  {
    "id": "sneaker-001",
    "name": "经典款运动鞋",
    "category": "运动鞋",
    "material": "透气网面 + EVA 鞋底",
    "sizes": ["39", "40", "41", "42", "43", "44"],
    "colors": ["白色", "黑色", "灰色"],
    "features": ["轻便", "防滑", "透气"],
    "suitable_scene": "日常跑步、健身、休闲穿着",
    "price": 299,
    "stock": 500
  },
  {
    "id": "jacket-002",
    "name": "轻量跑步风衣",
    "category": "外套",
    "material": "聚酯纤维 + 防水涂层",
    "sizes": ["M", "L", "XL", "XXL"],
    "colors": ["深蓝", "荧光绿"],
    "features": ["防风", "防水", "轻量"],
    "suitable_scene": "跑步、骑行、户外活动",
    "price": 399,
    "stock": 200
  }
]
```

**faq.json**

```json
[
  {
    "question": "退换货需要什么条件",
    "answer": "商品不影响二次销售，签收后 7 天内可申请退换货"
  },
  {
    "question": "多久能发货",
    "answer": "现货商品 48 小时内发货，预售商品以页面标注为准"
  }
]
```

### 与现有 Tool 的关系

```
Mock 版本现（不变）：
  mock_product_tool.get_mock_product_info()
  → 返回硬编码的同一双鞋

Knowledge Base 版本（新增）：
  kb_product_tool.query_product(query_text)
  → 本地 JSON 查询 + 关键词匹配

Node 内可以配置：
  if USE_KNOWLEDGE_BASE:
      product_info = kb_product_tool.query_product(text)
  else:
      product_info = mock_product_tool.get_mock_product_info()
```

### 作品集价值

展示"数据从文件读取"比"数据硬编码在代码里"更专业。而且方便后续接入真实数据库。

---

## 六、模块 4：SQLite 会话保存

### 解决什么短板

- **之前：** 所有数据在内存，关了终端全丢
- **之后：** 可以查历史对话，可以展示"这轮 Agent 走了什么路径"

### 目录位置

```
app/db/
├── __init__.py
├── database.py       # 初始化 + CRUD
└── models.py         # Pydantic 模型
```

### 存储内容

```
sessions     → session_id, created_at, message_count
messages     → session_id, role, content, created_at
agent_runs   → session_id, user_message, reply, intent,
               emotion, customer_stage, selected_skill,
               policy_decision, need_human, logs_json
```

### 在 FastAPI 中的使用

```python
@app.post("/api/chat")
def chat(req: ChatRequest):
    # FastAPI 层
    state = create_initial_state(...)
    result = run_graph(state)

    # 持久化
    db.save_message(session.id, "user", req.user_message)
    db.save_message(session.id, "assistant", result["reply"])
    db.save_agent_run(session.id, result)

    return ChatResponse(session_id=session.id, reply=result["reply"], ...)
```

### 作品集价值

面试官可以问："你怎么保存和分析对话？"
你的回答：SQLite 保存每轮 run 的完整 state，可以做后续分析。

---

## 七、模块 5：真实 LLM 回复润色

### 解决什么短板

- **之前：** "您咨询的商品信息如下：商品名称：经典款运动鞋" — 很模板
- **之后：** "这款经典款运动鞋采用透气网面和 EVA 鞋底，39-44 码可选，非常适合日常跑步和健身穿着～有什么具体想了解的吗？" — 像真人

### 严格边界

```
✅ LLM 可以做的事：
   text_analysis 文本分析摘要增强
   generate_reply 回复润色（在 Policy 结果确定后）

❌ LLM 绝对不能做的事：
   决定退款策略          → refund_policy 负责
   决定转人工            → escalation_policy 负责
   自行调用 Tool         → route_to_skill 路由
   绕过 logs 记录        → 每个节点固定写入
   修改执行结果          → skill_result 由 Skill 生成
```

### 润色流程

```
generate_reply 改造前（模板版本）：
  policy_decision = "retention"
  reply = "非常抱歉……首次退款……先帮您确认……"

generate_reply 改造后（LLM 润色版本）：
  policy_decision = "retention"
  base_reply = "非常抱歉……首次退款……先帮您确认……"
  reply = llm_polish(base_reply, emotion, intent)
  # LLM 只润色语言，不改变事实
```

### LLM 调用降级

```python
def llm_polish(text: str, emotion: str, intent: str) -> str:
    """LLM 润色回复，失败时返回原文。"""
    try:
        response = claude_api.call(prompt)
        return response.text
    except Exception:
        return text  # 降级：返回模板原文
```

### 为什么这个模块对作品集重要

| 维度 | 纯模板 | LLM 润色 |
|------|--------|---------|
| 技术难度 | 低 | 中 |
| 面试亮点 | 一般 | **"我知道 LLM 边界"** |
| 安全性 | 天生安全 | 需要设计安全边界 |
| 用户体验 | 生硬 | 自然 |

**面试官看到 LLM 润色 + Policy 控制，会认为你理解了 LLM 的工程化使用，而不是只会调 API。**

---

## 八、目录结构调整

### 当前结构

```
langgraph-agent-harness-v4/
├── app/
│   ├── graph.py
│   ├── main.py
│   ├── state/
│   ├── nodes/
│   ├── skills/
│   ├── tools/
│   ├── policies/
│   ├── memory/
│   └── tests/
├── docs/
├── README.md
├── CLAUDE.md
├── requirements.txt
└── .gitignore
```

### 增强后结构

```
langgraph-agent-harness-v4/
├── app/
│   ├── graph.py            # 不变
│   ├── main.py             # 不变（CLI 仍然可用）
│   ├── state/              # 不变
│   ├── nodes/              # 不变
│   ├── skills/             # 不变
│   ├── tools/              # 不变
│   ├── policies/           # 不变
│   ├── memory/             # 不变
│   ├── api/                # ★ 新增：FastAPI
│   │   ├── server.py
│   │   └── schemas.py
│   ├── db/                 # ★ 新增：SQLite
│   │   ├── database.py
│   │   └── models.py
│   ├── llm/                # ★ 新增：LLM 调用
│   │   └── client.py
│   ├── web/                # ★ 新增：Streamlit
│   │   └── st_app.py
│   └── tests/              # 不变 + 新增
│       └── test_api.py
├── data/                   # ★ 新增：知识库数据
│   ├── products.json
│   ├── faq.json
│   └── refund_policy.md
├── docs/                   # 不变
├── README.md               # 更新
├── requirements-mvp.txt    # ★ 新增：额外依赖
└── .env.example            # 更新：LLM API key 配置
```

### 关键原则

```
原有节点代码一行不改
新增模块在 app/ 下新建目录
CLI 模式仍然可用（python -m app.main）
```

---

## 九、分阶段实施计划

### Phase A：FastAPI + Web Demo（2 天）

**目标：** 把 CLI 项目包装成可访问的 Web 服务

| 任务 | 文件 |
|------|------|
| 创建 FastAPI 应用 | `app/api/server.py` |
| 创建请求/响应模型 | `app/api/schemas.py` |
| 集成 run_graph 调用 | `app/api/server.py` |
| 创建 Streamlit 页面 | `app/web/st_app.py` |
| 启动脚本 | 更新 README |

**验收：**
- `uvicorn app.api.server:app` 启动成功
- 浏览器打开 `localhost:8000` 看到聊天页面
- 输入文本能正常回复
- 页面展示 intent / emotion / skill / logs

### Phase B：SQLite 持久化（1 天）

**目标：** 对话不再丢失

| 任务 | 文件 |
|------|------|
| 创建 database 模块 | `app/db/database.py` |
| FastAPI 集成保存 | `app/api/server.py` |
| 启动自动建表 | `app/db/database.py` |

**验收：**
- 对话后 SQLite 文件中有记录
- 重启后历史可见

### Phase C：本地知识库（1 天）

**目标：** mock 数据从文件读取

| 任务 | 文件 |
|------|------|
| 创建 products.json | `data/products.json` |
| 创建 faq.json | `data/faq.json` |
| 创建知识库查询 tool | `app/tools/kb_tool.py` |

**验收：**
- 输入"有没有适合跑步的鞋" → 返回知识库中的商品信息
- 数据从 JSON 读取，不是硬编码

### Phase D：LLM 润色（2 天）

**目标：** 回复更自然

| 任务 | 文件 |
|------|------|
| 创建 LLM 调用模块 | `app/llm/client.py` |
| 修改 generate_reply 支持 LLM 润色 | `app/nodes/generate_reply.py` |
| 降级策略 | LLM 失败时回退模板 |

**验收：**
- LLM 启用时回复更自然
- LLM 不可用时回复为模板原文
- 退款决策仍然由 Policy 控制
- 转人工仍然由 Policy 控制

### 5 天总计划

```
Day 1-2:  FastAPI + Web Demo（最快见效）
Day 3:    SQLite 持久化
Day 4:    本地知识库
Day 5:    LLM 润色 + 集成测试 + README 更新
```

---

## 十、每阶段验收标准

### Phase A 验收

| # | 验收项 |
|---|--------|
| 1 | `uvicorn app.api.server:app` 启动成功 |
| 2 | `curl POST /api/chat` 返回正常回复 |
| 3 | `streamlit run app/web/st_app.py` 启动成功 |
| 4 | 浏览器聊天页面可用 |
| 5 | 页面展示 intent、emotion、selected_skill |
| 6 | 页面展示 logs trace |
| 7 | 原有 60 个 pytest 全部通过 |

### Phase B 验收

| # | 验收项 |
|---|--------|
| 1 | 对话后 SQLite 文件生成 |
| 2 | 数据库中 messages 表有记录 |
| 3 | 数据库中 agent_runs 表有完整 state |
| 4 | 重启后历史对话可见 |

### Phase C 验收

| # | 验收项 |
|---|--------|
| 1 | data/products.json 包含至少 3 个商品 |
| 2 | data/faq.json 包含至少 5 条 FAQ |
| 3 | "推荐一款跑鞋" → 返回知识库商品 |
| 4 | "怎么退货" → 返回知识库 FAQ |
| 5 | 知识库不可用时 mock 数据兜底 |

### Phase D 验收

| # | 验收项 |
|---|--------|
| 1 | LLM 润色后回复不包含模板痕迹 |
| 2 | LLM 失败时自动降级为模板 |
| 3 | 退款策略仍然由 refund_policy 控制 |
| 4 | 转人工仍然由 escalation_policy 控制 |
| 5 | logs 记录 LLM 是否被调用 |

---

## 十一、明确不做什么

| 不做 | 原因 |
|------|------|
| **飞书机器人** | 需要企业号配置，不适合作品集展示 |
| **Dify 知识库** | Phase A-D 已够，Dify 增加部署成本 |
| **n8n 自动化** | 作品集不需要展示工单系统 |
| **真实电商 API** | 需要商家授权 |
| **复杂前端** | Streamlit 够用，不需要 React |
| **Docker** | 当前阶段增加复杂度 |
| **用户认证** | MVP 阶段不需要 |
| **多轮对话记忆** | 单轮 query→response 已够展示 |
| **重写 nodes** | 保持 V4-lite 核心不变 |
| **降低测试覆盖** | 60 个 pytest 必须保持通过 |

---

## 十二、README 更新要点

增强版 README 需新增：

```
## Web Demo
Streamlit 聊天页面，支持文本和图片输入，展示 intent / emotion / logs trace

## API
FastAPI 提供 POST /api/chat 接口

## 知识库
本地商品和 FAQ JSON，数据驱动而非硬编码

## 会话保存
SQLite 持久化，重启不丢

## LLM 增强
回复润色 + 安全边界（不决策、不执行）
```

---

> **下一阶段建议：** 进入 **Phase A**，实现 FastAPI 包装 + Streamlit 聊天页面。
