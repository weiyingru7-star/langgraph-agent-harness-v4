# LangGraph 电商客服 Agent Harness — 作品集概述

> 基于 LangGraph + FastAPI + Next.js + DeepSeek + RAG 的可控型电商客服 Agent 作品集项目。

---

## 项目定位

本项目不是普通 Chatbot，而是一个 **Agent Harness**（智能体运行框架）。

### 核心区别

| 维度 | 普通 Chatbot | Agent Harness |
|------|-------------|---------------|
| 回复生成 | LLM 一次性生成 | Structured → RAG → Policy → Reply |
| 知识来源 | LLM 训练数据 | 本地商品 JSON + RAG 文档 |
| 退款决策 | LLM 可能乱承诺 | Policy 代码控制 |
| 可观测性 | 黑盒 | 每个节点有 Trace |
| 业务路由 | LLM 决定 | LangGraph 路由 |
| 多轮上下文 | 靠 LLM 记忆 | Context Loader + SQLite |

---

## 解决的问题

| 问题 | 方案 |
|------|------|
| 回复不像真人 | DeepSeek 润色 + 自然语言组织 |
| 乱承诺退款/补发 | Policy 强规则 + Safety 检查 |
| 不问产品名直接问尺码 | Context Loader + Product QA Resolver |
| 售后政策不知道 | 本地 RAG + evidence |
| "那个遮阳帽" 不理解 | LLM Semantic Parser |
| 无法排查错误 | Agent Trace + SQLite 持久化 |

---

## 架构亮点

### 结构化 + RAG 混合知识库

```
问题类型路由：
  size/price/color/material → products.json（结构化）
  refund_policy/保养/物流 → TF-IDF RAG（文档检索）
  两者都无 → 澄清 / 转人工
```

### LLM 只负责理解，Code 负责决策

```
LLM 做的：
  - 回复润色
  - 语义理解（Semantic Parser）
  - 基于 evidence 生成回答

Code 做的：
  - 退款决策 → refund_policy.py
  - 转人工 → escalation_policy.py
  - 退款/投诉强规则 → classify_intent.py
  - Safety 检查 → safety.py
```

### 可解释 Agent Trace

前端展示：
- intent / emotion / skill 来源
- RAG evidence + source_file
- Semantic Parser 输出
- 执行日志 (11 个节点)
- 原始 API 响应

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | Python + FastAPI + Uvicorn |
| Agent 框架 | LangGraph (StateGraph) |
| 结构化数据 | data/products.json (本地商品库) |
| 非结构化检索 | TF-IDF + 余弦相似度 (纯 Python) |
| LLM Provider | DeepSeek Chat API (可切换 mock) |
| 持久化 | SQLite (messages / agent_runs / handoffs) |
| 前端 | Next.js 14 + TypeScript |
| 测试 | pytest (219 个) |
| 语义解析 | LLM Semantic Parser + Code 校验 |

---

## 当前完成度

- [x] FastAPI POST /api/chat 接口
- [x] LangGraph 11 节点线性流程
- [x] 意图识别 (规则 + LLM Semantic Parser)
- [x] 多轮上下文 (SQLite Context Loader)
- [x] Structured 商品问答 (尺码/价格/材质/颜色)
- [x] 本地 RAG 文档检索 (售后政策/保养/FAQ)
- [x] DeepSeek 回复润色
- [x] DeepSeek 基于 evidence 的 RAG 回答
- [x] Policy 安全边界 (退款/投诉/转人工)
- [x] SQLite 持久化
- [x] Next.js 产品级 Demo
- [x] Agent Trace (intent / skill / evidence / semantic_parse)

---

## 后续可扩展方向

- **RAG 升级**：从 TF-IDF 升级为 Chroma/FAISS + embedding
- **Dify 接入**：对接 Dify 知识库做企业级 RAG
- **真实订单 API**：对接电商平台订单/物流 API
- **用户系统**：多用户 + Session 管理
- **管理后台**：对话记录 + 数据分析看板
- **多轮 RAG**：基于历史的 query rewrite
- **多语言**：支持英文等语言
- **Docker 部署**：容器化一键启动
