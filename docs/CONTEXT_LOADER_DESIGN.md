# Context Loader 设计 — CONTEXT_LOADER_DESIGN

> **Phase 10.9 · 设计文档**
> 目标：让 Agent 不只是保存历史，还能读取最近几轮消息用于多轮上下文理解。

---

## 一、为什么要做 Context Loader

### 当前的短板

```
Phase 10.8 完成：
  /api/chat → Agent 运行 → 结果写入 SQLite
                                ↓
                            成功保存了历史
                                ↓
                        但 Agent 不会读历史
```

SQLite 保存了 messages 和 agent_runs，但每一轮 /api/chat 仍然是**独立处理**——Agent 不知道上一轮说过什么。

### 电商客服常见追问

用户不会每轮都说全上下文，而是自然追问：

| 场景 | 第一轮 | 第二轮 | 没有上下文会怎样 |
|------|--------|--------|----------------|
| 尺码 | "这个衣服是什么材质" | "有什么码数" | 不知道问哪个商品 |
| 适合度 | "这款防晒衣怎么样" | "30岁适合吗" | 不知道在问防晒衣 |
| 推荐 | "有没有推荐" | "还有别的吗" | 不记得刚才推荐了什么 |
| 售后 | "这个破了能退吗" | "那怎么退" | 不知道在说退款的事 |
| 颜色 | "这个有黑色吗" | "多少钱" | 不知道问哪个商品 |

### Context Loader 解决什么

```
之前：每一轮 /api/chat 从头开始
  "有什么码数" → Agent 不知道是哪个商品 → 泛回答

之后：载入最近 10 条历史消息到 state["conversation_history"]
  "有什么码数" + 历史中"这款 UPF50+ 轻薄防晒衣"
    → Agent 知道用户还在问防晒衣 → 回答尺码
```

---

## 二、当前问题示例

### 没有 Context Loader

```
用户：这个衣服是什么材质？
AI（防晒衣详情）：这款 UPF50+ 轻薄防晒衣，锦纶混纺面料……

用户：有什么码数？
AI（没有上下文）：您好，我在的。请问有什么可以帮您？
→ smalltalk！因为 classify_intent 关键词"码数"在新一轮中没有历史商品信息辅助
```

### 有 Context Loader

```
用户：这个衣服是什么材质？
AI（防晒衣详情）……

第二轮开始前，Context Loader 从 SQLite 读取最近 10 条消息
写入 state["conversation_history"] = [
  {"role": "user", "content": "这个衣服是什么材质"},
  {"role": "assistant", "content": "这款 UPF50+ 轻薄防晒衣……"},
]

用户：有什么码数？
product_qa_skill 看到历史中有"UPF50+ 轻薄防晒衣"
→ 回答防晒衣尺码 S/M/L/XL
→ 不再答非所问
```

---

## 三、数据来源

### 主要来源：SQLite messages 表

```sql
SELECT role, content, created_at
FROM messages
WHERE session_id = ?
ORDER BY created_at ASC
LIMIT 10;
```

读取最近 10 条消息（按时间正序），结构化为：

```python
state["conversation_history"] = [
    {"role": "user", "content": "这个衣服是什么材质"},
    {"role": "assistant", "content": "这款 UPF50+ 轻薄防晒衣，锦纶混纺面料……"},
]
```

### 可选来源：agent_runs 表

如果需要更精确的上轮结果（如 matched_product、selected_skill、knowledge_source）：

```sql
SELECT intent, selected_skill, logs_json
FROM agent_runs
WHERE session_id = ?
ORDER BY created_at DESC
LIMIT 1;
```

第一版可以先只读 messages。agent_runs 作为后续增强。

### 没有历史时的行为

```python
# SQLite 查询为空
conversation_history = []
# 所有节点正常处理，不报错
```

---

## 四、State 设计

### 新增可选字段

第一版建议在 `CustomerServiceState` 中新增一个可选字段：

```python
# app/state/customer_state.py

class CustomerServiceState(TypedDict):
    # ... 原有字段保持不变 ...
    
    # Phase 10.9 新增：多轮上下文
    conversation_history: List[Dict[str, str]]
    """最近几轮对话历史（从 SQLite 读取），用于多轮追问理解。
       格式：[{"role": "user"/"assistant", "content": "..."}]
       第一版只读不写，由 Context Loader 在 graph 运行前注入。"""
```

### 不新增的字段

| 字段 | 不做 | 原因 |
|------|------|------|
| `context_summary` | ❌ | 需要 LLM 总结，当前阶段没有 LLM |
| `current_focus_product` | ❌ | 各 skill 可从 conversation_history 自行提取 |
| `user_profile` | ❌ | 跨 session，过度设计 |

---

## 五、接入位置设计

### 推荐方案 A（首选）

在 FastAPI `chat_api.py` 中，`create_initial_state` 之后、`run_graph` 之前：

```
/api/chat 收到请求
    ↓
create_initial_state(session_id, user_message, image_url)
    ↓
Context Loader: 从 SQLite 读取最近 10 条 messages
    ↓
state["conversation_history"] = history
    ↓
run_graph(state)  ← 后续节点可以读取 conversation_history
    ↓
继续保存本轮消息 + agent_run
```

**为什么选方案 A：**

| 维度 | 方案 A（API 层注入） | 方案 B（新增 LangGraph node） |
|------|---------------------|------------------------------|
| 改动范围 | 只改 chat_api.py | 需改 graph.py + 新增 node |
| 图结构 | 不变 | 需要调整边 |
| 测试影响 | 小 | 大 |
| 作品集展示 | 一样可说明 | 略复杂 |

### chat_api.py 修改示意

```python
def handle_chat(req: ChatRequest) -> ChatResponse:
    # 1. 创建初始 state
    initial = create_initial_state(
        session_id=req.session_id,
        user_message=req.user_message,
        image_url=req.image_url,
    )

    # 2. Context Loader：加载历史
    history = sqlite_store.get_messages(req.session_id, limit=10)
    if history:
        # 只保留 role 和 content，去除 id/image_url/created_at 等工具字段
        cleaned = [{"role": m["role"], "content": m["content"]} for m in history]
        initial["conversation_history"] = cleaned

    # 3. 运行 graph
    state = run_graph(initial)

    # 4. 持久化
    sqlite_store.save_message(...)
    sqlite_store.save_agent_run(...)
    # ...
```

---

## 六、上下文使用规则

### rules of thumb

```
1. 历史只做参考，不覆盖当前 user_message
2. 历史不能绕过 Policy 决策
3. 历史不能导致误退款
4. 纯图片/投诉/转人工场景不受历史影响
```

### product_qa_skill 中使用

当当前 `user_message` 命中追问关键词时，往上看最近的 assistant 回复：

```python
def _find_previous_product(conversation_history: list) -> str | None:
    """从历史中查找最近提到的商品名。"""
    product_names = ["UPF50+ 轻薄防晒衣", "轻量运动外套", "可折叠遮阳帽"]
    for msg in reversed(conversation_history):
        if msg["role"] == "assistant":
            for name in product_names:
                if name in msg["content"]:
                    return name
    return None

def run_product_qa_skill(state: dict) -> dict:
    text = state.get("user_message", "") or ""
    history = state.get("conversation_history", [])

    # 如果是追问，尝试从历史获取商品上下文
    followup_keywords = ["码数", "适合吗", "怎么洗", "还有别的吗",
                         "这个呢", "那款呢", "多大", "什么颜色", "多少钱"]
    if any(kw in text for kw in followup_keywords) and history:
        product_name = _find_previous_product(history)
        if product_name:
            # 用商品名增强当前文本
            text = f"{product_name} {text}"

    # 后续用增强后的 text 查知识库
    faq_result = query_faq(text, "product_question")
    product_result = query_product(text)
    # ...
```

### 追问关键词触发条件

| 关键词 | 推测意图 |
|--------|---------|
| 码数、尺码、多大 | 继续问上一轮商品尺码 |
| 适合吗、能穿吗 | 继续问上一轮商品适合度 |
| 怎么洗、保养、清洗 | 继续问上一轮商品保养 |
| 还有别的吗、还有什么 | 继续上一轮推荐 |
| 这个呢、那款呢 | 指代上一轮商品 |
| 什么颜色、黑色有吗、颜色 | 继续问上一轮商品颜色 |
| 多少钱、价格、价位 | 继续问上一轮商品价格 |

### 不应用上下文的场景

```
❌ intent = complaint → 历史不能阻止转人工
❌ intent = refund_request → 历史不能绕过 refund_policy
❌ need_human = True → 历史不能降低转人工优先级
❌ modality = image_only → 历史不能触发退款
```

---

## 七、不同 session 隔离

### 核心原则

```
session A 的历史 → 只能影响 session A
session B 的历史 → 只能影响 session B
```

### 如何保证

```python
# Context Loader 中
history = sqlite_store.get_messages(req.session_id, limit=10)
#            ↑                            ↑
#        全局函数                 只查当前 session_id
```

### 测试验证

```python
# session A：第一轮
call_api("A", "这个衣服是什么材质")
# session A：第二轮 — 应该能看到历史
state_a2 = call_api("A", "有什么码数")
assert "防晒衣" in state_a2["reply"]  # 结合历史

# session B：第一轮（独立，不应该看到 session A 的历史）
state_b1 = call_api("B", "你好")
assert "防晒衣" not in state_b1["reply"]  # 没有历史污染
```

---

## 八、不要过度设计

### 第一版做

```
✅ 从 SQLite messages 表读取最近 10 条消息
✅ 写入 state["conversation_history"]
✅ product_qa_skill 读取历史辅助追问
✅ 不同 session 隔离
✅ 无历史时正常处理
```

### 第一版不做

| 不做 | 原因 |
|------|------|
| **LLM 总结历史** | 当前没有 LLM，关键词匹配够用 |
| **向量记忆** | 小数据量不需要 |
| **跨 session 记忆** | 安全原因 |
| **用户画像** | 过度设计 |
| **Redis** | SQLite 已够用 |
| **修改 graph.py** | 方案 A 不改主流程 |
| **新 LangGraph node** | 方案 A API 层注入 |
| **历史覆盖当前输入** | 当前 user_message 始终是权威 |
| **历史绕过 Policy** | 退款 / 转人工仍受 Policy 控制 |

---

## 九、测试设计

新增 `tests/test_context_loader.py`：

| # | 测试 | 断言 |
|---|------|------|
| 1 | 有历史时读取最近 messages | `len(history) > 0` |
| 2 | 无历史时不报错 | `conversation_history = []`，不崩溃 |
| 3 | 第一轮问材质 → 第二轮问码数 | 第二轮 reply 含尺码，非 smalltalk |
| 4 | 第一轮问推荐 → 第二轮问适合 | 第二轮 reply 结合上轮商品 |
| 5 | 不同 session 不串上下文 | session A 历史不影响 session B |
| 6 | 纯图片场景不受历史影响 | `modality=image_only` 仍追问 |
| 7 | 退款场景不受历史影响 | refund_policy 仍控制 |
| 8 | pytest 全部通过 | — |

---

## 十、禁止事项

| 禁止 | 原因 |
|------|------|
| 不接 LLM | 关键词匹配已够用 |
| 不做长期记忆 | 只需近几轮 |
| 不做跨用户记忆 | 安全 |
| 不接 Redis | SQLite 已够 |
| 不接向量库 | 数据量小 |
| 不改变 refund_policy.py | Policy 仍然控制 |
| 不让上下文绕过转人工 | escalation_check 仍然控制 |
| 不让历史导致误退款 | Policy 不变 |
| 不把历史拼成 prompt 给 LLM | 无 LLM |

---

## 十一、Phase 10.10 实现边界

### 允许修改

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/api/chat_api.py` | **修改** | create_initial_state 后注入 conversation_history |
| `app/state/customer_state.py` | **修改** | 新增 conversation_history 可选字段 |
| `app/skills/product_qa_skill.py` | **修改** | 读取 history 辅助追问 |
| `app/tests/test_context_loader.py` | **新建** | 多轮上下文测试 |
| `README.md` | 少量补充 | — |

### 不得修改

| 文件 | 原因 |
|------|------|
| `app/graph.py` | 主流程不变，方案 A 在 API 层注入 |
| `app/policies/` | 退款/转人工规则不变 |
| `app/persistence/sqlite_store.py` | 已有 get_messages 足够 |
| `app/tools/` | 知识库工具不变 |
| `app/web/` | 大幅 UI 不修改 |
| `tests/` 已有测试 | 不删除、不降低覆盖 |

---

## 十二、验收标准

| # | 验收项 | 验证方式 |
|---|--------|---------|
| 1 | `pytest` 全部通过 | 运行测试 |
| 2 | CLI 仍然可用 | `.venv/bin/python -m app.main` |
| 3 | FastAPI 仍然可用 | `uvicorn app.server:app` |
| 4 | Streamlit 仍然可用 | `streamlit run` |
| 5 | 第一轮"衣服材质" → 第二轮"有什么码数" | 第二轮 reply 含尺码（非 smalltalk） |
| 6 | 第一轮"推荐" → 第二轮"30岁适合吗" | 第二轮 reply 结合上轮商品 |
| 7 | session A 历史不影响 session B | 断言互不污染 |
| 8 | 无历史时不报错 | `conversation_history=[]` 正常 |
| 9 | 退款 / 投诉场景仍受 Policy 控制 | — |
| 10 | SQLite 只读不写（写仍在 chat_api 末尾） | 代码审查 |

---

> **下一阶段建议：** 进入 **Phase 10.10**，根据本文档实现 Context Loader。
