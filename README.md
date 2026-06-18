# LangGraph 电商客服 Agent Harness V4-lite

> 基于 Python + LangGraph 构建的电商客服 Agent Harness 学习项目，支持文本、图片、图文输入，具备意图识别、情绪识别、客户阶段判断、Skill 路由、Policy 规则、Mock Tool、多模态路由、回复生成和测试验证。

---

## 项目目标

本项目不是普通的 Prompt Demo，也不是简单的 RAG 客服机器人，而是一个 **Agent Harness 学习项目**。

**Agent Harness** 指一套可控、可追踪、可测试、可扩展的智能体运行框架。核心区别在于：
- Prompt Demo：把全部逻辑塞进 prompt，LLM 直接决定一切，行为不可控、不可追踪。
- Agent Harness：LLM 负责"理解"，LangGraph 负责"流转"，代码（Skill/Tool/Policy）负责"执行"。

目标是用 LangGraph 搭建一个电商客服 Agent，重点学习：
1. 如何用图（Graph）管理多步骤对话流程
2. 如何将业务规则与 LLM 解耦
3. 如何让每个节点可观测、可测试
4. 如何设计可扩展的 Agent 架构

---

## 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.13 | 运行时 |
| LangGraph | 状态图框架，控制流程流转 |
| langchain-core | 基础组件 |
| TypedDict | 状态模型定义 |
| pytest | 测试框架（60 个测试） |
| Claude Code + Superpowers | AI 辅助开发 |

---

## 核心架构

```
┌─────────────────────────────────────────────────────┐
│  State — CustomerServiceState (TypedDict)           │
│  所有节点共享的"数据包"，包含会话输入、分析结果、     │
│  路由结果、策略决策、回复、日志等 21 个字段          │
├─────────────────────────────────────────────────────┤
│  Nodes — LangGraph 节点（11 个线性节点）             │
│  parse_input → decide_modality → analyze_text/       │
│  analyze_multimodal → classify_intent →              │
│  classify_emotion → classify_stage → route_to_skill  │
│  → escalation_check → generate_reply → save_log      │
├─────────────────────────────────────────────────────┤
│  Skills — 客服业务能力（7 个）                        │
│  product_qa / recommendation / logistics             │
│  / refund / exchange / complaint / human              │
├─────────────────────────────────────────────────────┤
│  Tools — 外部系统 mock（3 个）                       │
│  mock_product_tool / mock_order_tool                  │
│  / mock_multimodal_tool                               │
├─────────────────────────────────────────────────────┤
│  Policies — 确定性业务规则（2 个）                    │
│  refund_policy / escalation_policy                    │
├─────────────────────────────────────────────────────┤
│  Memory — 会话上下文保存                             │
│  基于 session_id 的简易内存 dict                       │
├─────────────────────────────────────────────────────┤
│  Logs / Errors — 可观测性                            │
│  每个节点写入 logs，出错时触发转人工兜底               │
├─────────────────────────────────────────────────────┤
│  Tests — 全路径验证                                  │
│  60 个 pytest 覆盖所有场景路径                        │
└─────────────────────────────────────────────────────┘
```

---

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
              ┌────────────┼──────────────┐
              ▼            ▼              ▼
       ┌──────────┐ ┌──────────┐ ┌──────────────┐
       │text_only │ │image_only│ │text_with_    │
       │          │ │          │ │image         │
       └────┬─────┘ └────┬─────┘ └──────┬───────┘
            │            │              │
            ▼            ▼              ▼
     ┌──────────┐ ┌──────────┐ ┌────────────────┐
     │analyze_  │ │ 追问回复 │ │analyze_        │
     │text      │ │不调多模态│ │multimodal      │
     └────┬─────┘ └────┬─────┘ └───────┬────────┘
          │            │               │
          └────────────┼───────────────┘
                       ▼
                ┌─────────────────┐
                │ classify_intent  │
                └────────┬────────┘
                       ▼
                ┌──────────────────┐
                │ classify_emotion  │
                └────────┬─────────┘
                       ▼
                ┌─────────────────┐
                │ classify_stage   │
                └────────┬────────┘
                       ▼
                ┌──────────────────┐
                │  route_to_skill   │
                └────────┬─────────┘
                       ▼
                ┌──────────────────┐
                │ escalation_check  │
                └────────┬─────────┘
                       ▼
                ┌──────────────────┐
                │  generate_reply   │
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

```bash
# 进入项目目录
cd langgraph-agent-harness-v4

# 创建虚拟环境
python3 -m venv .venv

# 安装依赖
.venv/bin/pip install -r requirements.txt

# 运行主程序（展示多种客服场景）
.venv/bin/python -m app.main

# 运行全部测试
.venv/bin/python -m pytest -v
```

---

## Demo 输入样例

运行 `python -m app.main` 后会依次展示以下场景：

```
"我的快递怎么还没到"          → 物流查询
"质量太差了我要退款"          → 退款请求 + 情绪识别
"这个衣服是什么材质"          → 商品咨询
"我要人工，太生气了"          → 转人工
"你们这个太垃圾了，我要投诉"  → 投诉处理
"我要换个尺码"                → 换货请求
"你好，在吗"                  → 闲聊兜底
(纯图片)                      → 图片追问
"这个破了能退吗" + 图片       → 图文多模态
"这个怎么安装" + 安装图片     → 先文字后图片
```

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
│   ├── graph.py              # LangGraph 图定义
│   ├── main.py               # 入口 + demo
│   ├── state/                # CustomerServiceState
│   ├── nodes/                # 11 个 LangGraph 节点
│   ├── skills/               # 7 个客服 Skill
│   ├── tools/                # 3 个 Mock Tool
│   ├── policies/             # 2 个 Policy 规则
│   ├── memory/               # 会话记忆
│   └── tests/                # 60 个 pytest
├── docs/                     # 8 份设计文档
├── requirements.txt
├── CLAUDE.md
└── README.md
```

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [docs/STATE_DESIGN.md](docs/STATE_DESIGN.md) | 状态设计 |
| [docs/GRAPH_DESIGN.md](docs/GRAPH_DESIGN.md) | 图流程设计 |
| [docs/CLASSIFICATION_DESIGN.md](docs/CLASSIFICATION_DESIGN.md) | 分类节点设计 |
| [docs/SKILL_POLICY_DESIGN.md](docs/SKILL_POLICY_DESIGN.md) | Skill/Tool/Policy 设计 |
| [docs/REPLY_DESIGN.md](docs/REPLY_DESIGN.md) | 回复生成设计 |
| [docs/MULTIMODAL_DESIGN.md](docs/MULTIMODAL_DESIGN.md) | 多模态路由设计 |
| [docs/PROJECT_SUMMARY_DESIGN.md](docs/PROJECT_SUMMARY_DESIGN.md) | 项目总结设计 |
