# 落地 MVP 架构设计 — DEPLOYMENT_MVP_DESIGN

> **Phase 11.1 · 设计文档**
> 目标：2 周内将 V4-lite 从本地 CLI 学习项目升级为最小真实客服系统。

---

## 一、当前 V4-lite 和落地 MVP 的差距

### V4-lite 当前状态

```
V4-lite 定位：本地 CLI 学习项目

输入方式: CLI 手动创建 initial_state
理解能力: 关键词规则（classify_intent / classify_emotion）
回复生成: 模板字符串（generate_reply）
多模态: mock 数据
外部知识: 无
会话保存: 内存 dict，关闭即丢
转人工: need_human 字段，无实际通知
部署方式: .venv/bin/python -m app.main
```

### MVP 目标状态

```
MVP 定位：可演示的最小客服系统

输入方式: Web 聊天页面 → FastAPI → Agent
理解能力: 真实 LLM（Claude API）做分类 + 分析
回复生成: 真实 LLM 润色回复
外部知识: Dify 知识库查询商品/售后资料
会话保存: SQLite 持久化
转人工: need_human=true → n8n webhook → 飞书通知
部署方式: docker compose up（FastAPI + Agent + SQLite）
```

### 不做什么

| 不做 | 原因 |
|------|------|
| 真实退款 | 安全风险，MVP 只做信息查询 |
| 真实订单 API | 需要商家授权，超出 MVP 范围 |
| 用户登录系统 | 2 周不够，先做匿名会话 |
| 多轮复杂对话 | 保持单轮 query → response 模式 |
| 多租户 | 2 周不够 |
| 生产部署 | MVP 只做可演示原型 |

---

## 二、MVP 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    用户 (浏览器)                          │
└─────────────────────────────────────────────────────────┘
                           │
                     HTTP POST /chat
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Server                         │
│                                                         │
│  POST /chat → 接收 user_message + session_id + image    │
│         ↓                                               │
│   创建 initial_state → 调用 LangGraph agent             │
│         ↓                                               │
│   LangGraph 返回完整 state → 保存到 SQLite              │
│         ↓                                               │
│   返回 reply + intent + need_human 给前端               │
└─────────────────────────────────────────────────────────┘
           │                      │
           ▼                      ▼
┌──────────────────┐   ┌──────────────────────────┐
│   LangGraph      │   │    LLM 服务               │
│   Agent Harness  │   │                          │
│                   │   │  classify_intent → LLM   │
│   复用 V4-lite    │   │  classify_emotion → LLM  │
│   节点逻辑        │   │  generate_reply → LLM    │
│                   │   │  multimodal → LLM Vision │
│   修改：替换      │   │                          │
│   关键词规则     │   │  通过 httpx 调用 API      │
│   → LLM 调用     │   └──────────────────────────┘
│                   │              │
│   模板回复       │              ▼
│   → LLM 润色     │   ┌──────────────────────────┐
│                   │   │    Dify 知识库            │
└──────────────────┘   │                          │
           │           │   product_qa → 查商品资料 │
           ▼           │   after_sale → 查售后政策 │
┌──────────────────┐   │                          │
│   SQLite         │   └──────────────────────────┘
│                  │
│   sessions       │              │
│   messages       │              ▼
│   agent_runs     │   ┌──────────────────────────┐
│                  │   │    n8n Webhook            │
└──────────────────┘   │                          │
                       │   need_human=true         │
                       │   → 推送飞书通知          │
                       └──────────────────────────┘
```

---

## 三、新增模块设计

### 1. FastAPI 服务层

**文件：** `app/api/server.py`

职责：
- 提供 `POST /chat` 接口
- 接收用户输入 → 调用 `run_graph()` → 返回结果
- 管理 session_id（首次请求自动生成）

```python
# 伪代码示意
@app.post("/chat")
async def chat(request: ChatRequest):
    # 1. 从 SQLite 读取或创建 session
    session = get_or_create_session(request.session_id)

    # 2. 构建 initial_state
    state = create_initial_state(
        session_id=session.id,
        user_message=request.message,
        image_url=request.image_url,
    )

    # 3. 调用 LangGraph agent
    result = run_graph(state)

    # 4. 保存到 SQLite
    save_message(session.id, "user", request.message)
    save_message(session.id, "assistant", result["reply"])
    save_agent_run(session.id, result)

    # 5. 如果 need_human，触发 webhook
    if result["need_human"]:
        trigger_human_webhook(session.id, result)

    # 6. 返回
    return ChatResponse(
        reply=result["reply"],
        intent=result["intent"],
        need_human=result["need_human"],
    )
```

### 2. LLM 调用模块

**文件：** `app/llm/client.py`

职责：
- 封装 Claude API 调用
- 提供 `classify_intent(text)`, `classify_emotion(text)`, `generate_reply(state)` 等方法

设计原则：

```
LLM 调用模块 = 替换关键词规则 + 模板回复
接口与 V4-lite 节点保持一致
改动只在节点内部，Graph 结构不变
```

```python
# 伪代码：替换 classify_intent 节点
# Phase 4 版本（关键词）：
def classify_intent(state):
    text = state["user_message"]
    for intent, conf, keywords in RULES:
        if any(kw in text for kw in keywords):
            return intent, conf
    return "smalltalk", 0.3

# MVP 版本（LLM）：
def classify_intent(state):
    text = state["user_message"]
    prompt = f"分析用户意图，从以下列表中选择一个：{INTENTS}\n用户说：{text}"
    result = llm.call(prompt)  # Claude API
    return result.intent, result.confidence
```

### 3. SQLite 数据层

**文件：** `app/db/database.py`

职责：
- 创建和操作 SQLite 数据库
- 保存 sessions、messages、agent_runs

### 4. Web 聊天页面

**文件：** `app/web/index.html`

- 单页 HTML，内嵌 CSS + JS
- 聊天输入框 + 消息展示
- 调用 `/chat` API
- 支持打字机效果显示回复

### 5. n8n Webhook 通知

**配置：**
- 项目中保留 webhook URL 配置项
- `need_human=true` 时 POST 到 n8n webhook
- n8n 工作流负责推送到飞书群机器人

---

## 四、API 设计

### POST /chat

**请求：**

```json
{
  "session_id": "uuid-xxx",
  "message": "我的快递怎么还没到",
  "image_url": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `session_id` | string | 否 | 为空时服务端自动生成 |
| `message` | string | 是 | 用户文本输入 |
| `image_url` | string | 否 | 图片 URL（可选） |

**响应：**

```json
{
  "session_id": "uuid-xxx",
  "reply": "感谢您的耐心等待，我来帮您查看一下物流信息……",
  "intent": "logistics_question",
  "emotion": "anxious",
  "customer_stage": "in_sale",
  "need_human": false,
  "human_reason": null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `session_id` | string | 会话 ID |
| `reply` | string | 客服回复 |
| `intent` | string | 识别的意图 |
| `emotion` | string | 情绪标签 |
| `customer_stage` | string | 客户阶段 |
| `need_human` | bool | 是否需要转人工 |
| `human_reason` | string | 转人工原因 |

### GET /health

**响应：** `{"status": "ok", "version": "mvp-1.0"}`

---

## 五、数据库表设计

### sessions 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | session_id |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 最后活动时间 |

### messages 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | — |
| session_id | TEXT | 关联 session |
| role | TEXT | user / assistant / system |
| content | TEXT | 消息内容 |
| created_at | TIMESTAMP | 发送时间 |

### agent_runs 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | — |
| session_id | TEXT | 关联 session |
| user_message | TEXT | 用户输入 |
| reply | TEXT | 客服回复 |
| intent | TEXT | 意图 |
| emotion | TEXT | 情绪 |
| emotion_score | REAL | 情绪评分 |
| customer_stage | TEXT | 客户阶段 |
| selected_skill | TEXT | 路由的 skill |
| policy_decision | TEXT | 策略决策 |
| need_human | BOOLEAN | 转人工标记 |
| human_reason | TEXT | 转人工原因 |
| llm_classify | BOOLEAN | 是否使用 LLM 分类 |
| lat_ms | INTEGER | 处理耗时 |
| created_at | TIMESTAMP | 执行时间 |

### SQL 建表语句

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_message TEXT,
    reply TEXT,
    intent TEXT,
    emotion TEXT,
    emotion_score REAL,
    customer_stage TEXT,
    selected_skill TEXT,
    policy_decision TEXT,
    need_human BOOLEAN DEFAULT 0,
    human_reason TEXT,
    llm_classify BOOLEAN DEFAULT 0,
    lat_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

---

## 六、LLM 接入边界

### 接入范围

| 模块 | 当前（V4-lite） | MVP |
|------|----------------|-----|
| classify_intent | 关键词规则 | **替换为 LLM** |
| classify_emotion | 关键词规则 | **替换为 LLM** |
| generate_reply | 模板字符串 | **替换为 LLM 润色** |
| multimodal_analysis | mock 数据 | **保留 mock**（LLM Vision 留到后期） |
| refund_policy | 代码规则 | **保持代码规则** |
| escalation_policy | 代码规则 | **保持代码规则** |

### 不允许 LLM 做的事

```
❌ LLM 不能决定是否退款
    → refund_policy.py 仍然负责

❌ LLM 不能决定是否转人工
    → escalation_policy.py 仍然负责

❌ LLM 不能直接执行业务动作
    → Skill 负责执行，Tool 负责外部访问

❌ LLM 不能绕过 logs 记录
    → 每个节点仍然写入 state["logs"]
```

### 升级方式

每个 LLM 调用作为独立模块，节点内部调用：

```
classify_intent.py 改造前：
    keywords → intent

classify_intent.py 改造后：
    llm_call(prompt) → intent  ← 接口不变，Graph 不受影响
```

---

## 七、Dify 知识库接入边界

### 接入方式

通过 Dify API 查询知识库，作为 Tool 集成：

```python
def query_dify_knowledge(query: str, dataset_id: str) -> str:
    """查询 Dify 知识库，返回相关文档片段。"""
    response = httpx.post(
        f"{DIFY_BASE_URL}/v1/datasets/{dataset_id}/retrieve",
        headers={"Authorization": f"Bearer {DIFY_API_KEY}"},
        json={"query": query},
    )
    return response.json()
```

### 查询场景

| 场景 | Dify 数据集 | 查询内容 |
|------|------------|---------|
| product_question | 商品知识库 | 商品规格、材质、使用方法 |
| after_sale | 售后政策库 | 退换货政策、保修范围 |
| logistics | 物流知识库 | 配送范围、时效说明 |

### Dify 不做什么

```
❌ Dify 不做退款决策
❌ Dify 不做情绪判断
❌ Dify 不做路由决策
❌ Dify 不代替 LLM 理解
```

---

## 八、n8n 转人工流程

### 触发条件

当 `state["need_human"] == True` 时，FastAPI 触发 n8n webhook：

```python
def trigger_human_webhook(session_id: str, state: dict):
    """通过 n8n webhook 推送飞书人工通知。"""
    payload = {
        "session_id": session_id,
        "user_message": state["user_message"],
        "intent": state["intent"],
        "emotion": state["emotion"],
        "emotion_score": state["emotion_score"],
        "customer_stage": state["customer_stage"],
        "human_reason": state["human_reason"],
        "agent_reply": state["reply"],
        "created_at": datetime.now().isoformat(),
    }
    httpx.post(N8N_WEBHOOK_URL, json=payload)
```

### n8n 工作流

```
Webhook 接收
    ↓
格式化飞书消息卡片
    ↓
POST 到飞书群机器人 webhook
    ↓
飞书群内出现：
  🔴 转人工通知
  会话：xxx
  用户说：质量太差了我要退款
  原因：情绪评分过高
  客服回复：……
```

### n8n webhook 配置

```
环境变量：
  N8N_WEBHOOK_URL=https://your-n8n.example.com/webhook/cs-human
  FEISHU_BOT_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

---

## 九、安全边界

| 原则 | 说明 |
|------|------|
| **不自动退款** | 即使 LLM 说"已退款"，实际不执行任何退款操作 |
| **不执行业务动作** | MVP 只做信息查询和回复，不修改订单 |
| **LLM 不决策** | 退款、转人工决策仍由 Policy 控制 |
| **日志全记录** | 每一轮 agent run 都持久化到 SQLite |
| **输入长度限制** | 限制 user_message 不超过 2000 字符 |
| **防止 prompt injection** | LLM prompt 中不包含退款/转人工决策权限 |
| **不做用户认证** | MVP 匿名访问，无敏感数据 |

---

## 十、分阶段实施计划

### Phase A：FastAPI 包装（2 天）

**目标：** 把 CLI 项目包成 API

| 任务 | 说明 |
|------|------|
| 新增 `app/api/server.py` | FastAPI 服务 |
| 新增 `app/db/database.py` | SQLite 初始化 |
| 新增 `requirements-mvp.txt` | 添加 httpx, uvicorn, fastapi |
| 测试 | 命令行 curl 测试 `/chat` 接口 |

**验收：** `curl http://localhost:8000/chat` 返回客服回复

### Phase B：LLM 替换（3 天）

**目标：** 替换关键词规则 + 模板回复

| 任务 | 说明 |
|------|------|
| 新增 `app/llm/client.py` | Claude API 封装 |
| 修改 `classify_intent.py` | 关键词 → LLM |
| 修改 `classify_emotion.py` | 关键词 → LLM |
| 修改 `generate_reply.py` | 模板 → LLM 润色 |
| 测试 | 对比 LLM 版本和关键词版本的 intent 差异 |

**验收：** 输入"这个怎么用" → LLM 识别为 product_question

### Phase C：Web 聊天页面（2 天）

**目标：** 提供简单网页聊天入口

| 任务 | 说明 |
|------|------|
| 新增 `app/web/index.html` | 单页聊天页面 |
| FastAPI 增加静态文件路由 | 提供 HTML |
| 测试 | 浏览器打开页面可以正常聊天 |

**验收：** 浏览器输入 `localhost:8000` 看到聊天界面

### Phase D：n8n 转人工（2 天）

**目标：** need_human=true 时通知飞书

| 任务 | 说明 |
|------|------|
| 新增 n8n webhook 调用 | FastAPI 中触发 |
| 配置示例环境变量 | `.env.example` 更新 |
| 测试 | 手动触发 need_human 验证飞书通知 |

**验收：** 输入"我要投诉" → 飞书群收到通知

### Phase E：Dify 知识库（2 天）

**目标：** 商品/售后查询走 Dify 知识库

| 任务 | 说明 |
|------|------|
| 新增 `dify_query` tool | Dify API 调用 |
| 修改 `product_qa_skill` | Dify 知识库 + mock 兜底 |
| 测试 | "这个衣服怎么洗" → 返回知识库内容 |

**验收：** 输入商品问题 → 回复中包含知识库信息

### 2 周总计划

```
Week 1:
  Mon-Tue: Phase A (FastAPI + SQLite)
  Wed-Fri: Phase B (LLM 替换)

Week 2:
  Mon-Tue: Phase C (Web 页面)
  Wed:     Phase D (n8n 转人工)
  Thu-Fri: Phase E (Dify 知识库) + 集成测试
```

---

## 十一、每阶段验收标准

### Phase A 验收

| # | 验收项 |
|---|--------|
| 1 | `.venv/bin/python -m app.api.server` 启动成功 |
| 2 | `curl -X POST localhost:8000/chat -d '{"message":"你好"}'` 返回 reply |
| 3 | SQLite 数据库中能查到 messages |
| 4 | `GET /health` 返回 200 |
| 5 | 现有 pytest 仍然通过 |

### Phase B 验收

| # | 验收项 |
|---|--------|
| 1 | 输入"这个怎么用" → intent = product_question |
| 2 | 输入"我要退款" → intent = refund_request + policy_decision = retention |
| 3 | 输入"气死了" → emotion = angry + score > 0.85 |
| 4 | 输入"我的快递什么时候到" → reply 是自然语言，不是模板 |
| 5 | 退款决策仍然由 refund_policy 控制 |
| 6 | 转人工仍然由 escalation_policy 控制 |

### Phase C 验收

| # | 验收项 |
|---|--------|
| 1 | 浏览器访问 `localhost:8000` 看到聊天页面 |
| 2 | 输入消息后能显示回复 |
| 3 | session 刷新后能继续对话 |
| 4 | 页面移动端可用（响应式） |

### Phase D 验收

| # | 验收项 |
|---|--------|
| 1 | need_human=true 时触发 n8n webhook |
| 2 | 飞书群收到人工通知卡片 |
| 3 | need_human=false 时不触发 |

### Phase E 验收

| # | 验收项 |
|---|--------|
| 1 | 商品咨询时 Dify 知识库被查询 |
| 2 | 知识库信息出现在回复中 |
| 3 | Dify 不可用时 mock 数据兜底 |
| 4 | Dify 不做退款/转人工决策 |

---

> **下一阶段建议：** 进入 **Phase A**，实现 FastAPI 包装 + SQLite 持久化。
