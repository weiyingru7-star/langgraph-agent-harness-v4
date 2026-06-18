# Streamlit Web Demo 设计 — STREAMLIT_DEMO_DESIGN

> **Phase 10.3 · 设计文档**
> 目标：新增 Streamlit 页面，让用户通过浏览器体验 LangGraph 电商客服 Agent。

---

## 一、为什么要加 Streamlit

### 当前的问题

```
当前作品集展示方式：
  ┌─ README.md ─────────────────────┐
  │  "运行 .venv/bin/python -m ..." │
  │  "然后看 JSON 输出"              │
  └──────────────────────────────────┘

面试官或访客需要：
  1. clone 项目
  2. 创建 venv
  3. 安装依赖
  4. 运行 CLI
  5. 理解 JSON 输出

→ 门槛太高，大部分人看到"CLI only"就放弃了
```

### Streamlit 解决什么

```
Streamlit 展示方式：
  ┌─ 浏览器打开 ────────────────────┐
  │  输入文字 → 看到回复             │
  │  同时看到 intent / emotion / skill │
  │  展开看到 logs trace              │
  │  一键填充示例场景                  │
  └──────────────────────────────────┘

访客只需要：
  1. 打开链接（或一行 streamlit run）
  2. 打字聊天
  3. 看到效果
```

### Streamlit vs 其他方案

| 方案 | 学习成本 | 展示效果 | 开发速度 |
|------|---------|---------|---------|
| Streamlit | 低（纯 Python） | 中（够用） | 快（几小时） |
| React + FastAPI | 高（前后端联调） | 高（可定制） | 慢（几天） |
| Gradio | 低 | 中 | 快 |
| CLI only | 无 | 差（JSON 文本） | 已完成 |

**选 Streamlit 的理由：** 最快让作品集"看得见"。作品集面试官不会在意你用 Streamlit 还是 React，能展示运行效果就行。

---

## 二、新增技术栈

| 技术 | 用途 | 版本 |
|------|------|------|
| Streamlit | Web 展示框架 | >=1.40 |
| httpx 或 requests | 调用 FastAPI | 已装 |

### 组件调用关系

```
Streamlit页面 ←──HTTP──→ FastAPI (/api/chat) ←──→ LangGraph Agent
    │                         │
    │                     Pydantic 模型
    │                     CustomerServiceState
    │
仅展示层                   核心逻辑层
不写业务判断               不修改
```

---

## 三、目录设计

```
app/web/
├── __init__.py              # 包标记
└── streamlit_app.py         # Streamlit 页面
```

---

## 四、页面功能设计

### 页面布局

```
┌──────────────────────────────────────────────────────────┐
│  LangGraph 电商客服 Agent  · Demo                         │
├──────────────────────────────────────────────────────────┤
│  ┌ 示例场景 ──────────────────────────────────────────┐ │
│  │ [我的快递怎么还没到] [质量太差了我要退款] [商品咨询]  │ │
│  │ [我要人工] [闲聊] [纯图片] [图文测试]                │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌ 输入 ───────────────────────────────────────────────┐ │
│  │ session_id: [demo-xxx                  ] (自动生成) │ │
│  │ user_message: [                         ]          │ │
│  │ image_url: [（可选）                    ]          │ │
│  │ □ 返回完整 state  □ 显示 logs trace                │ │
│  │ [发送]                                              │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌ 对话 ───────────────────────────────────────────────┐ │
│  │                                                     │ │
│  │ 你: 我的快递怎么还没到                                │ │
│  │                                                     │ │
│  │ AI: 感谢您的耐心等待，我来帮您查看一下物流信息。     │ │
│  │ 您的快递已发货，单号 SF1234567890……                  │ │
│  │                                                     │ │
│  │ ── 分析结果 ──────────                              │ │
│  │ 意图: logistics_question                            │ │
│  │ 情绪: anxious (0.65)                                │ │
│  │ 客户阶段: in_sale                                   │ │
│  │ 路由技能: logistics_skill                           │ │
│  │ 策略决策: —                                         │ │
│  │ 转人工: 否                                          │ │
│  │                                                     │ │
│  │ ── 执行日志 (11 步) ──                              │ │
│  │ 🟢 parse_input                                      │ │
│  │ 🟢 decide_modality → text_only                      │ │
│  │ 🟢 classify_intent → logistics_question             │ │
│  │ 🟢 route_to_skill → logistics_skill                 │ │
│  │ 🟢 generate_reply                                   │ │
│  │ 🟢 save_log                                         │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 页面元素说明

| 元素 | 说明 |
|------|------|
| **示例场景按钮** | 一键填充输入框，方便快速体验 |
| **session_id** | 自动 UUID 生成，可选手动输入 |
| **user_message** | 用户文本输入 |
| **image_url** | 可选的图片 URL |
| **发送按钮** | 调用 FastAPI |
| **对话展示** | 用户输入 + AI 回复 |
| **分析结果面板** | intent, emotion, customer_stage, selected_skill, policy_decision, need_human |
| **执行日志 trace** | 展开显示 11 个节点的执行过程 |
| **完整 state** | 可选：显示完整 JSON state |

---

## 五、Demo 场景快捷按钮

设计 7 个快捷按钮，点击后自动填充输入框。

| # | 按钮标签 | user_message | image_url |
|---|---------|-------------|-----------|
| 1 | 📦 物流查询 | 我的快递怎么还没到 | — |
| 2 | 💰 退款请求 | 质量太差了我要退款 | — |
| 3 | 👕 商品咨询 | 这个衣服是什么材质 | — |
| 4 | 🫵 转人工 | 我要人工，太生气了 | — |
| 5 | 👋 闲聊 | 你好，在吗 | — |
| 6 | 🖼️ 纯图片 | (空) | `https://example.com/test.jpg` |
| 7 | 🔍 图文测试 | 这个破了能退吗 | `https://example.com/broken.jpg` |

---

## 六、运行方式

### 步骤 1：启动 FastAPI（终端 1）

```bash
cd langgraph-agent-harness-v4
.venv/bin/python -m uvicorn app.server:app --reload --port 8003
```

### 步骤 2：启动 Streamlit（终端 2）

```bash
.venv/bin/python -m streamlit run app/web/streamlit_app.py
```

### 步骤 3：打开浏览器

Streamlit 默认在 `http://localhost:8501` 启动。

---

## 七、接口调用设计

### 调用代码（伪代码）

```python
# streamlit_app.py 中的调用逻辑
import streamlit as st
import httpx

FASTAPI_URL = "http://127.0.0.1:8003"

def call_agent(session_id, user_message, image_url, return_full_state):
    """调用 FastAPI /api/chat 接口。"""
    try:
        resp = httpx.post(
            f"{FASTAPI_URL}/api/chat",
            json={
                "session_id": session_id,
                "user_message": user_message,
                "image_url": image_url,
                "image_base64": None,
                "return_full_state": return_full_state,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        st.error("⛔ FastAPI 未启动，请执行：")
        st.code(".venv/bin/python -m uvicorn app.server:app --reload --port 8003")
        return None
    except Exception as e:
        st.error(f"调用异常: {e}")
        return None
```

### 请求示例

```json
{
  "session_id": "demo-streamlit-001",
  "user_message": "我的快递怎么还没到",
  "image_url": null,
  "image_base64": null,
  "return_full_state": true
}
```

### 响应展示

```python
# 展示分析结果
col1, col2 = st.columns(2)
col1.metric("意图", data["intent"])
col1.metric("情绪", f"{data['emotion']} ({data['emotion_score']})")
col2.metric("客户阶段", data["customer_stage"])
col2.metric("路由技能", data["selected_skill"])
col2.metric("转人工", "是" if data["need_human"] else "否")

# 展示 logs trace
if show_logs:
    for log in data.get("logs", []):
        st.text(f"🟢 {log['node']} — {log['summary']}")
```

---

## 八、错误处理

### 场景 1：FastAPI 没启动

```
页面显示：
  ⛔ 无法连接到 FastAPI 服务
  📋 请启动：
  .venv/bin/python -m uvicorn app.server:app --reload --port 8003
  🔄 刷新页面重试
```

### 场景 2：API 返回错误

```
页面显示：
  ⚠️ 服务返回错误: {错误信息}
  session_id 保持不变
  输入框内容保持不变
  ❌ 不编造回复
```

### 场景 3：网络超时

```
页面显示：
  ⏱️ 请求超时，请重试
  不丢失已有对话记录
```

### 错误处理原则

```
✅ 友好提示，不让页面崩溃
✅ 显示解决步骤
✅ 保留已有对话记录
✅ 不编造回复
❌ 不吞掉错误
❌ 不在 Streamlit 侧伪造 state
```

---

## 九、禁止事项

| 禁止 | 原因 |
|------|------|
| **在 Streamlit 里重写 Agent 逻辑** | Streamlit 只是展示层 |
| **在 Streamlit 里写 intent 判断** | 应走 FastAPI → Agent |
| **在 Streamlit 里写 emotion 判断** | 同上 |
| **在 Streamlit 里编造 reply** | 必须来自 Agent |
| **在 Streamlit 里绕过 escalation_check** | 不允许 |
| **修改现有 Node / Skill / Policy** | 保持主线不被破坏 |
| **删除 CLI 入口** | CLI 模式必须继续可用 |
| **降低测试覆盖** | 新增功能不能破坏现有测试 |

---

## 十、Phase 10.4 实现边界

### 允许修改/新增的文件

| 文件 | 操作 |
|------|------|
| `app/web/__init__.py` | **新建** |
| `app/web/streamlit_app.py` | **新建** |
| `requirements.txt` | 补充 `streamlit` |
| `README.md` | 补充 Web Demo 运行方式 |

### 不得修改的文件

| 文件 | 原因 |
|------|------|
| `app/state/` | 核心设计 |
| `app/nodes/` | 核心逻辑 |
| `app/skills/` | 核心逻辑 |
| `app/policies/` | 核心逻辑 |
| `app/tools/` | 核心逻辑 |
| `app/api/` | 已完成且稳定 |
| `app/server.py` | 已完成 |
| `app/tests/` | 现有测试不能破坏 |

---

## 十一、验收标准

| # | 验收项 | 验证方式 |
|---|--------|---------|
| 1 | `pytest` 全部通过 | 运行测试 |
| 2 | `uvicorn app.server:app --port 8003` 可用 | 启动 + curl |
| 3 | `streamlit run app/web/streamlit_app.py` 可启动 | 启动 + 浏览器访问 |
| 4 | 页面输入文本能得到回复 | 页面操作 |
| 5 | 页面展示 intent / emotion / selected_skill / need_human | 页面查看 |
| 6 | 页面展示 logs trace | 页面查看 |
| 7 | 示例场景按钮可一键填充 | 页面操作 |
| 8 | FastAPI 未启动时页面有友好提示 | 只启动 Streamlit |
| 9 | 没有修改 Agent Harness 核心逻辑 | git diff |
| 10 | CLI 模式仍然可用 | `.venv/bin/python -m app.main` |

---

> **下一阶段建议：** 进入 **Phase 10.4**，根据本文档实现 Streamlit 页面。
