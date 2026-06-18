# SQLite 会话保存设计 — SQLITE_PERSISTENCE_DESIGN

> **Phase 10.7 · 设计文档**
> 目标：为 Agent Harness 增加 SQLite 持久化能力，保存每次用户消息和 Agent 运行记录。

---

## 一、为什么要加 SQLite

### 当前短板

| 问题 | 现状 | 影响 |
|------|------|------|
| Streamlit 刷新丢失 | session_state 刷新即丢 | 测试需要重头开始 |
| memory 是内存 dict | `conversation_memory.py` 使用 `_store: dict` | 程序关闭全丢 |
| Agent run 没有日志 | 每次运行结果只在 state 中，不保存 | 无法回溯分析 |
| 无法统计分析 | 不知道哪些意图出现最多 | 知识库缺口分析 |
| 转人工无记录 | need_human=true 没有持久化 | 无法统计服务质量 |

### 增强价值

```
之前：Agent 跑完 → state 输出 → 没了
之后：Agent 跑完 → state 输出 → 自动保存到 SQLite

价值：
  🔍 调试：翻历史 state 看哪一层出错
  📊 分析：统计各 intent 出现频率
  📋 质检：查看转人工记录
  📈 后续：可升级到数据看板、客服分析
```

---

## 二、数据库位置

```
data/app.db     ← 运行时数据库（.gitignore 不提交）
data/app.db     ← 不存在时自动创建
```

测试时使用内存模式或临时路径：

```python
# 测试用
sqlite_store.init_db(":memory:")
```

> 注意：`data/app.db` 加入 `.gitignore`，不提交真实运行数据。
> `data/products.json`、`data/faq.json`、`data/refund_policy.md` 继续提交。

---

## 三、表结构设计

### 1. messages — 消息记录

```sql
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_session ON messages(session_id, created_at);
```

| 字段 | 说明 |
|------|------|
| `role` | `user` / `assistant` / `system` |
| `content` | 消息文本正文 |
| `image_url` | 图片 URL（可选） |
| `created_at` | 发送时间 |

### 2. agent_runs — Agent 运行记录

```sql
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_message TEXT,
    image_url TEXT,
    modality TEXT,
    intent TEXT,
    intent_confidence REAL,
    emotion TEXT,
    emotion_score REAL,
    customer_stage TEXT,
    selected_skill TEXT,
    policy_decision TEXT,
    need_human BOOLEAN DEFAULT 0,
    human_reason TEXT,
    reply TEXT,
    logs_json TEXT,
    errors_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agent_runs_session ON agent_runs(session_id, created_at);
```

| 字段 | 说明 |
|------|------|
| `user_message` | 用户输入的文本 |
| `image_url` | 图片 URL |
| `modality` | 模态（text_only / image_only / text_with_image） |
| `intent` ~ `human_reason` | Agent 分析结果 |
| `reply` | 最终回复 |
| `logs_json` | 执行日志（JSON 字符串） |
| `errors_json` | 错误信息（JSON 字符串） |
| `created_at` | 运行时间 |

---

## 四、目录设计

```
app/persistence/
├── __init__.py
└── sqlite_store.py
```

第一版简单方案，不引入 SQLAlchemy，直接使用 Python 标准库 `sqlite3`。

---

## 五、sqlite_store.py 设计

### 函数接口

```python
def init_db(db_path: str = "data/app.db") -> None:
    """初始化数据库，创建表结构（幂等）。"""

def save_message(session_id: str, role: str, content: str, image_url: str | None = None) -> None:
    """保存消息。"""

def save_agent_run(session_id: str, state: dict) -> None:
    """保存 Agent 运行记录。保存 logs_json 和 errors_json 为 JSON 字符串，不保存 conversations 等冗余字段。"""

def get_messages(session_id: str, limit: int = 20) -> list:
    """读取指定会话的消息。"""

def get_agent_runs(session_id: str, limit: int = 20) -> list:
    """读取指定会话的 Agent 运行记录。"""

def clear_db(db_path: str) -> None:
    """清空所有数据（测试用）。"""
```

### 错误处理策略

```python
# 所有 save 方法使用 try/except 包裹
# 数据库失败不应影响用户获取回复

def save_agent_run(session_id: str, state: dict) -> None:
    try:
        conn = _get_conn()
        conn.execute("INSERT INTO agent_runs (...) VALUES (...)", ...)
        conn.commit()
    except Exception as e:
        print(f"[sqlite_store] 保存 agent_run 失败: {e}")
        # 不抛异常，不影响主流程
```

### 完整 save 流程（在 FastAPI chat_api.py 中）

```python
# /api/chat 调用成功后
persist_errors = []
try:
    sqlite_store.save_message(req.session_id, "user", req.user_message, req.image_url)
except Exception as e:
    msg = f"保存 user message 失败: {e}"
    print(f"[persistence] {msg}")
    persist_errors.append(msg)

try:
    sqlite_store.save_message(req.session_id, "assistant", state.get("reply", ""))
except Exception as e:
    msg = f"保存 assistant reply 失败: {e}"
    print(f"[persistence] {msg}")
    persist_errors.append(msg)

try:
    sqlite_store.save_agent_run(req.session_id, state)
except Exception as e:
    msg = f"保存 agent_run 失败: {e}"
    print(f"[persistence] {msg}")
    persist_errors.append(msg)

# 持久化错误附加到 response，不静默吞掉
if persist_errors:
    resp.errors.extend(persist_errors)
```

---

## 六、FastAPI 集成设计

```python
# chat_api.py 修改示意

def handle_chat(req: ChatRequest) -> ChatResponse:
    try:
        initial = create_initial_state(...)
        state = run_graph(initial)
    except Exception as e:
        return ChatResponse(errors=[...])

    # 构建响应
    resp = ChatResponse(...)

    # 持久化（不影响主流程，错误通过 print + response.errors 可见）
    persist_errors = []
    for record in _build_persist_records(req, state):
        try:
            sqlite_store.save_message(record["session_id"], record["role"], record["content"])
        except Exception as e:
            msg = f"保存 {record['role']} 消息失败: {e}"
            print(f"[persistence] {msg}")
            persist_errors.append(msg)

    try:
        sqlite_store.save_agent_run(req.session_id, state)
    except Exception as e:
        msg = f"保存 agent_run 失败: {e}"
        print(f"[persistence] {msg}")
        persist_errors.append(msg)

    if persist_errors:
        resp.errors.extend(persist_errors)

    return resp
```

### 原则

```
✅ 持久化失败 → 用户仍然拿到回复
✅ 持久化失败 → 错误通过 print 日志 + response.errors 可见
❌ 持久化不参与业务判断
❌ 不因数据库慢而延迟回复
❌ 不静默吞掉持久化错误（不使用 bare except: pass）
```

---

## 七、CLI 模式接入设计

CLI 入口 `app/main.py` 目前直接调用 `run_graph` 并打印 JSON。

持久化在 CLI 中的接入方式：

```python
# main.py 修改示意

from app.persistence.sqlite_store import save_message, save_agent_run, init_db

def run_with_persistence(session_id, user_message, image_url=None):
    """运行 Agent 并持久化结果。"""
    initial = create_initial_state(
        session_id=session_id,
        user_message=user_message,
        image_url=image_url,
    )
    state = run_graph(initial)

    # 持久化
    try:
        save_message(session_id, "user", user_message, image_url)
        save_message(session_id, "assistant", state.get("reply", ""))
        save_agent_run(session_id, state)
    except Exception as e:
        print(f"[persistence] 保存失败: {e}")

    return state
```

CLI 模式和使用 FastAPI 模式共用同一套 `sqlite_store`，行为一致。

---

## 八、Streamlit 展示设计

第一版不做复杂历史列表。只在右侧 debug expander 增加一行提示：

```
💾 本次运行已保存到 SQLite（data/app.db）
```

不修改 Streamlit 主体布局。

---

## 八、测试设计

新增 `tests/test_sqlite_persistence.py`：

| # | 测试 | 断言 |
|---|------|------|
| 1 | `init_db()` 能创建表 | 表存在 |
| 2 | `save_message("s1", "user", "你好")` 能保存 | 读取后 count=1 |
| 3 | `get_messages("s1")` 返回最近消息 | limit 有效 |
| 4 | `save_agent_run("s1", state)` 保存完整字段 | 读取后含 intent / emotion / reply |
| 5 | `get_agent_runs("s1")` 按时间倒序 | 最新在前 |
| 6 | `clear_db()` 清空所有表 | 全空 |
| 7 | 数据库失败不抛异常 | try/except 包裹 |
| 8 | `pytest` 全部通过 | — |

---

## 九、.gitignore 设计

```gitignore
# 之前已有内容...
.venv/
__pycache__/
.pytest_cache/

# 新增：不提交运行时数据库
data/app.db
*.db
*.sqlite
*.sqlite3

# data 下 json 和 md 仍提交
!data/*.json
!data/*.md
```

---

## 十、禁止事项

| 禁止 | 原因 |
|------|------|
| SQLite 不参与意图判断 | 分类在 classify_intent，不在数据库 |
| SQLite 不决定退款 | Policy 控制 |
| 业务规则不写进数据库 | Policy 代码唯一事实来源 |
| 不用 SQLite 替代 Policy | 不绕过 refund_policy.py |
| 不接 PostgreSQL | 第一版 SQLite 就够 |
| 不做复杂 ORM | 标准库 sqlite3 就够 |
| 不做后台管理页面 | 超出项目范围 |
| 不做数据看板 | 超出项目范围 |
| 不修改 graph.py 主流程 | 持久化在 API 层做 |

---

## 十一、Phase 10.8 实现边界

### 允许新增/修改

| 文件 | 操作 |
|------|------|
| `app/persistence/__init__.py` | **新建** |
| `app/persistence/sqlite_store.py` | **新建** |
| `app/api/chat_api.py` | **修改** — 调用 sqlite_store |
| `app/tests/test_sqlite_persistence.py` | **新建** |
| `.gitignore` | **修改** — 增加 `data/app.db` |
| `README.md` | 少量补充 |

### 不得修改

| 文件 | 原因 |
|------|------|
| `app/graph.py` | 主流程不变 |
| `app/state/` | 核心结构不变 |
| `app/policies/` | 退款/转人工规则不变 |
| `app/skills/` | 业务逻辑不变 |
| `app/tools/` | 知识库工具不变 |
| `app/web/` | 不写数据看板 |
| `app/nodes/` | 不参与持久化 |
| `app/server.py` | API 路由不变 |

---

## 十二、验收标准

| # | 验收项 | 验证方式 |
|---|--------|---------|
| 1 | `pytest` 全部通过 | 运行测试 |
| 2 | CLI 仍然可用 | `.venv/bin/python -m app.main` |
| 3 | FastAPI 仍然可用 | `uvicorn app.server:app` |
| 4 | Streamlit 仍然可用 | `streamlit run` |
| 5 | `/api/chat` 调用后 messages 表有记录 | 测试 |
| 6 | `/api/chat` 调用后 agent_runs 表有记录 | 测试 |
| 7 | `data/app.db` 不存在或不被 git 跟踪 | `git status` |
| 8 | 数据库失败不影响 Agent 回复 | 测试 + 代码审查 |
| 9 | 数据库只做持久化，不参与业务决策 | 代码审查 |

---

> **下一阶段建议：** 进入 **Phase 10.8**，根据本文档实现 SQLite 持久化。
