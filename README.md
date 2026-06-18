# LangGraph 电商客服 Agent Harness V4-lite

> 基于 LangGraph + FastAPI + Next.js + DeepSeek + RAG 的可控型电商客服 Agent 作品集项目。支持结构化商品问答、RAG 文档检索、多轮上下文、LLM 语义解析、Policy 安全边界。

---

## 项目定位

本项目不是普通 Chatbot，而是一个 **Agent Harness**（智能体运行框架）。核心区别：LLM 只负责理解和表达，Policy 负责决策，LangGraph 负责流转。

| 维度 | 普通 Chatbot | Agent Harness（本项目） |
|------|-------------|----------------------|
| 回复生成 | LLM 一次性生成 | Structured → RAG → Policy → Reply |
| 知识来源 | LLM 训练数据 | 本地商品 JSON + RAG 文档 |
| 退款决策 | LLM 可能乱承诺 | Policy 代码控制 |
| 可观测性 | 黑盒 | 每个节点有 Agent Trace |
| 业务路由 | LLM 决定 | LangGraph 路由 |

### 解决的问题

- 🎯 **商品咨询**：尺码/价格/材质/颜色走结构化字段，不走 LLM 编造
- 📚 **售后政策**：RAG 检索 evidence，带 source_file 引用
- 💬 **多轮上下文**：Context Loader + SQLite 持久化，追问不走丢
- 🧠 **语义理解**：LLM Semantic Parser 识别"那个遮阳帽""第二个怎么样"
- 🔒 **安全边界**：退款/投诉/人工强规则优先，LLM 不决策
- 🔍 **可解释**：Agent Trace 展示每个节点的 intent / skill / evidence

---

## 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.13 | 运行时 |
| LangGraph | 状态图框架，控制流程流转 |
| FastAPI | HTTP 接口 |
| SQLite | 会话持久化 |
| DeepSeek | LLM 润色 + RAG 回答 + 语义解析 |
| Next.js 14 | 产品级前端 Demo |
| TypeScript | 前端类型安全 |
| pytest | 219 个测试 |
| TypedDict | 状态模型定义 |

---

## 架构

```
用户输入 → Context Loader → Intent/Semantic Parser → Skill Router
    → Structured KB / RAG / Policy → Reply Composer → Response
```

```
app/
├── server.py              # FastAPI 入口 (+ CORS + .env 加载)
├── graph.py               # LangGraph 图定义 (11 节点)
├── state/                 # CustomerServiceState (TypedDict)
├── nodes/                 # LangGraph 节点
│   ├── classify_intent.py # 规则 + LLM Semantic Parser
│   ├── route_to_skill.py  # RAG / Structured / Policy 路由
│   └── generate_reply.py  # 模板 + DeepSeek 润色
├── skills/                # 客服业务能力
│   ├── product_qa_skill.py      # 结构化商品字段查询
│   ├── knowledge_qa_skill.py    # RAG 文档检索
│   ├── refund_skill.py          # 退款处理
│   └── recommendation_skill.py  # 商品推荐
├── llm/
│   ├── deepseek_provider.py  # DeepSeek API
│   ├── semantic_parser.py    # LLM 语义解析 + Code 校验
│   └── safety.py             # 输出安全检查
├── knowledge/
│   ├── rag_provider.py     # TF-IDF RAG 检索
│   ├── vector_store.py     # 简易向量存储
│   └── chunker.py          # 文档切片
├── persistence/
│   └── sqlite_store.py     # SQLite 持久化
└── tests/                  # 219 个 pytest
apps/web-next/              # Next.js 前端 Demo
data/                       # 商品 + FAQ 知识库
knowledge/raw/              # RAG 原始文档
docs/                       # 设计文档
```

## 完整流程图

```
                    ┌─────────────┐
                    │    START    │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │ parse_input │
                    └──────┬──────┘
                           ▼
                    ┌───────────────┐
                    │decide_modality│
                    └───────┬───────┘
                           │
              ┌────────────┼──────────────────┐
              ▼            ▼                  ▼
       ┌──────────┐ ┌──────────┐ ┌──────────────┐
       │text_only │ │image_only│ │text_with_    │
       │          │ │ 追问回复 │ │image         │
       └────┬─────┘ └────┬─────┘ └──────┬───────┘
            │            │              │
            ▼            ▼              ▼
     ┌──────────┐ ┌──────────────┐ ┌────────────────┐
     │classify_ │ │ 不调用多模态  │ │ mock 多模态     │
     │intent    │ │              │ │                │
     │+ Semantic│ │              │ │                │
     │Parser    │ │              │ │                │
     └────┬─────┘ └──────┬───────┘ └───────┬────────┘
          │              │                 │
          └──────────────┼─────────────────┘
                         ▼
                  ┌──────────────┐
                  │ route_to_skill│ ← Structured / RAG / Policy
                  └──────┬───────┘
                         ▼
                  ┌──────────────────┐
                  │ escalation_check │
                  └────────┬─────────┘
                         ▼
                  ┌──────────────────┐
                  │  generate_reply   │ ← DeepSeek 润色
                  └────────┬─────────┘
                         ▼
                  ┌─────────────┐
                  │  save_log   │
                  └──────┬──────┘
                         ▼
                  ┌─────────────┐
                  │     END     │
                  └─────────────┘
```

---

## 支持的场景

| # | 场景 | 输入示例 | 处理路径 |
|---|------|---------|---------|
| 1 | **物流查询** | "我的快递怎么还没到" | text → logistics_skill → 返回物流信息 |
| 2 | **商品咨询** | "这个衣服是什么材质" | text → product_qa_skill → 返回商品信息 |
| 3 | **售前推荐** | "推荐一款好用的手机" | text → recommendation_skill → 返回推荐商品 |
| 4 | **退款请求** | "质量太差了我要退款" | text → refund_skill → policy_decision 挽留 |
| 5 | **换货请求** | "我要换个尺码" | text → exchange_skill → 进入换货流程 |
| 6 | **投诉** | "你们这个太垃圾了，我要投诉" | text → complaint_skill → 转人工 |
| 7 | **转人工** | "我要人工，太生气了" | text → human_skill → need_human=True |
| 8 | **闲聊兜底** | "你好，在吗" | smalltalk_fallback → 问候回复 |
| 9 | **纯图片追问** | (只发图片，无文字) | image_only → 追问"请问您想咨询什么" |
| 10 | **图文多模态** | "这个破了能退吗" + 破损图片 | text_with_image → mock 图文分析 |
| 11 | **先文字后图片** | 先"这个怎么安装"，再发图片 | memory 合并 → 图文分析 |

---

## 为什么这是 Agent Harness，不是 Prompt Demo

### Prompt Demo 的做法

```
用户输入 → LLM（prompt 中写了所有规则）→ 回复
```

所有逻辑塞进 prompt，LLM 决定一切：
- 退款规则写在 prompt 里 → 容易被绕过
- 是否退款由 LLM 决定 → 不可控
- 每一步做了什么不可追踪 → 不可观测
- 修改任何规则都要改 prompt → 不可维护

### Agent Harness 的做法

```
用户输入 → 解析节点 → 意图/情绪分析节点 → 策略判断 → 技能执行节点 → 回复生成 → 日志
           ↑                        ↑                ↑                ↑
         LLM 只负责理解           Policy 负责规则   Skill 负责业务    Log 记录一切
```

### 关键差异

| 维度 | Prompt Demo | Agent Harness |
|------|-------------|---------------|
| **规则位置** | 写在 prompt 里 | 写在 Policy 代码里 |
| **决策方式** | LLM 直接决策 | Policy 代码判断 |
| **动作执行** | LLM 决定是否调用工具 | Graph 路由到指定 Skill |
| **可观测性** | LLM 输出即全部 | 每个节点有独立日志 |
| **可测试性** | 只能端到端测试 | 每个节点/策略可单独测试 |
| **可控性** | 低，LLM 可能"自由发挥" | 高，代码控制关键路径 |
| **可维护性** | 改需求 = 改 prompt | 改需求 = 改对应模块 |

### 具体体现

- **退款规则在 `refund_policy.py`**，不在 system prompt 里
- **转人工规则在 `escalation_policy.py`**，不由 LLM 判断
- **外部能力通过 mock tool**，不让 LLM 直接访问
- **每一步写入 `state["logs"]`**，可回放、可调试
- **pytest 覆盖全路径**，60 个测试验证每个节点行为

---

## 运行方式

### Docker Compose（推荐）

```bash
cd ~/langgraph-agent-harness-v4
docker compose up --build
```

浏览器打开 **http://localhost:3002**。后端 API 在 `http://localhost:8003`。

传入 DeepSeek API Key（可选）：

```bash
DEEPSEEK_API_KEY=你的key docker compose up --build
```

### 本地手动运行

```bash
# 终端 1：FastAPI 后端
cd ~/langgraph-agent-harness-v4
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.server:app --reload --port 8003

# 终端 2：Next.js 前端
cd ~/langgraph-agent-harness-v4/apps/web-next
npm install
npm run dev
```

浏览器打开 **http://localhost:3000**。

### 运行测试

```bash
.venv/bin/python -m pytest -v
```

### 开启 DeepSeek（可选）

在项目根目录创建 `.env`：

```bash
LLM_PROVIDER=deepseek
LLM_ENABLE_REPLY_POLISH=true
LLM_ENABLE_SEMANTIC_PARSER=true
DEEPSEEK_API_KEY=你的key
```

`.env` 不提交 Git。没有 `.env` 时使用 mock provider，不影响基本功能。

---

## Demo 场景

| 场景 | 输入 | 路径 |
|------|------|------|
| 商品咨询 | "这个衣服是什么材质" | product_qa_skill + DeepSeek 润色 |
| 尺码查询 | "运动外套有什么尺码" | Structured sizes |
| 售后政策 | "超过7天还能退吗" | RAG + evidence (refund_policy.md) |
| 保养说明 | "防晒衣怎么洗" | RAG (care_guide.md) |
| 语义理解 | "那个遮阳帽不错" | Semantic Parser + product_qa |
| 适合人群 | "运动外套我妈适合吗" | Semantic Parser + suitability |
| 退款请求 | "质量太差了我要退款" | refund_skill (Policy 控制) |
| 投诉转人工 | "我要找人工投诉" | complaint_skill (need_human=true) |

---

## 项目边界

当前 V4-lite 第一版 **没有接** 以下真实能力：

| 不做 | 原因 |
|------|------|
| 真实 LLM | 第一版用关键词规则 + 模板回复 |
| 真实多模态模型 | 使用 mock 数据 |
| 真实电商 API | 全部 mock |
| 数据库 | 数据在 State 中流转 |
| Dify / RAG 知识库 | 后续可接入 |
| 飞书机器人 | 第一版 CLI 运行 |
| n8n / 自动化 | 后续可接入 |
| Docker 部署 | 后续可容器化 |
| 前端页面 | 第一版纯后端 |

---

## 后续升级路线

| 阶段 | 升级内容 |
|------|---------|
| **短期** | 替换关键词规则为真实 LLM |
| **短期** | 替换 mock tool 为真实 API |
| **中期** | 接入 Dify / RAG 知识库 |
| **中期** | 接 FastAPI 提供 REST API |
| **中期** | 接前端页面（React / Vue） |
| **中期** | 接飞书机器人 |
| **中期** | 数据库持久化会话 |
| **长期** | Docker 容器化部署 |
| **长期** | 真实多模态模型接入 |
| **长期** | 多语言支持 |

---

## 开发方式

本项目采用分阶段增量开发：

1. **先设计** — 每个阶段先写设计文档（`docs/`）
2. **再实现** — 根据设计文档实现业务代码
3. **再测试** — 每个新增逻辑补 pytest
4. **再 Review** — Review 修正后合并
5. **Git checkpoint** — 每个阶段结束创建 git commit 便于回滚

### 开发阶段

| Phase | 内容 |
|-------|------|
| 0-1 | 项目骨架 + 文档 |
| 2 | CustomerServiceState 设计 + 实现 + 测试 |
| 3 | 最小 LangGraph 流程 + 图构建 + 测试 |
| 4 | 意图/情绪/阶段分类 + 关键词规则 + 测试 |
| 5 | Skill / Tool / Policy 分层 + 路由 + 测试 |
| 6 | 回复生成 + 模板 + 测试 |
| 7 | 多模态路由 + memory + 测试 |
| 8 | 项目收尾 + README |

---

## 项目结构

```
langgraph-agent-harness-v4/
├── app/
│   ├── server.py              # FastAPI 入口
│   ├── graph.py               # LangGraph 图定义
│   ├── state/                 # CustomerServiceState (TypedDict)
│   ├── nodes/                 # 11 个 LangGraph 节点
│   ├── skills/                # 客服业务 Skill
│   ├── llm/                   # DeepSeek Provider + Semantic Parser + Safety
│   ├── knowledge/             # RAG Provider + TF-IDF 向量存储
│   ├── persistence/           # SQLite 持久化
│   ├── api/                   # FastAPI 路由
│   ├── schemas/               # Pydantic 请求/响应模型
│   └── tests/                 # 219 个 pytest
├── apps/web-next/             # Next.js 前端 Demo
├── data/                      # 商品 JSON + FAQ + RAG 文档
├── docs/                      # 设计文档
├── evals/                     # Eval 测试集（test_cases.jsonl + 报告输出）
├── scripts/                   # 工具脚本（build_chroma_index.py, run_eval.py）
├── requirements.txt
├── CLAUDE.md
└── README.md
```

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [docs/PORTFOLIO_OVERVIEW.md](docs/PORTFOLIO_OVERVIEW.md) | 作品集概述 |
| [docs/STATE_DESIGN.md](docs/STATE_DESIGN.md) | 状态设计 |
| [docs/GRAPH_DESIGN.md](docs/GRAPH_DESIGN.md) | 图流程设计 |
| [docs/SKILL_POLICY_DESIGN.md](docs/SKILL_POLICY_DESIGN.md) | Skill/Tool/Policy 设计 |
| [docs/LOCAL_KNOWLEDGE_BASE_DESIGN.md](docs/LOCAL_KNOWLEDGE_BASE_DESIGN.md) | 本地知识库设计 |
| [docs/LLM_PROVIDER_DESIGN.md](docs/LLM_PROVIDER_DESIGN.md) | LLM Provider 设计 |
| [docs/HYBRID_RAG_DESIGN.md](docs/HYBRID_RAG_DESIGN.md) | 混合 RAG 设计 |
| [docs/SQLITE_PERSISTENCE_DESIGN.md](docs/SQLITE_PERSISTENCE_DESIGN.md) | SQLite 持久化设计 |
| [docs/EVAL_GUIDE.md](docs/EVAL_GUIDE.md) | Agent Eval 测试集 |

---

## Eval Test Suite

本仓库包含一套轻量端到端 Eval 测试集，用于验证 Agent 的意图识别、商品问答、RAG 检索、安全边界和回复质量。

**快速运行：**
```bash
.venv/bin/python scripts/run_eval.py
```

**当前状态（Mock Baseline）：**
- `evals/test_cases.jsonl` — 25 条固定测试用例
- 覆盖：商品问答、多轮上下文、RAG 知识库、安全边界、无资料兜底、物流、图片模态
- 通过率：**19/25 (76%)**
- 剩余 6 条依赖 LLM Semantic Parser（启用 `LLM_PROVIDER=deepseek` 后可通过）

**Eval 边界：**
- Eval 是额外质量评估，**不替代**单元测试（`app/tests/`）
- 默认使用 mock LLM + TF-IDF RAG，**零外部依赖**
- 生成的 `eval_report.json` **不提交** GitHub（已在 `.gitignore` 中排除）
- 详细说明见 [docs/EVAL_GUIDE.md](docs/EVAL_GUIDE.md)
