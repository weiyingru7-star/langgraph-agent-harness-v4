# 面试讲解稿

> 这不是让你背下来，而是帮你理清思路。
> 面试官问"你做过什么项目"时，挑下面的核心点说就行。

---

## 一、一句话说清项目

> **基于 LangGraph + DeepSeek + RAG 的电商客服 Agent 框架。**
> **核心思路：LLM 只负责理解和表达，业务决策（退款/转人工）由代码控制。**

---

## 二、项目解决了什么问题（当面试官问"为什么做这个"）

```
市面上很多 AI 客服就是调 API 让 LLM 回复，
但这样几个问题：
1. 退款规则写 prompt 里 → LLM 可能忽略或被绕过
2. 是否转人工由 LLM 判断 → 标准不统一
3. 出了错查不了 → 黑盒

我做的这个框架把流程拆成 11 个节点，
每个节点可单独测试、可追踪。
关键决策（退款、转人工）写在代码里，
LLM 只做它擅长的事——理解和表达。
```

---

## 三、为什么不是普通 Chatbot（高频问题）

| 维度 | 普通 Chatbot | 我的项目 |
|------|-------------|---------|
| 回复生成 | LLM 一次性生成 | Structured → RAG → Policy → Reply |
| 知识来源 | LLM 训练数据 | 本地 JSON + RAG 文档 |
| 退款决策 | LLM 可能乱承诺 | Policy 代码控制 |
| 可观测性 | 黑盒 | Agent Trace 每个节点可见 |

---

## 四、LangGraph 在哪里用（当面试官问 LangGraph）

```
我用 LangGraph 的 StateGraph 定义了 11 个节点。

每个节点是一个函数，读写同一个 TypedDict State。
节点之间用 add_edge 线性连接。

比如：
parse_input → decide_modality → classify_intent → route_to_skill
→ escalation_check → generate_reply → save_log

每个节点从 state 读数据，处理完写回 state。
这样新加一个节点不影响其他节点，可扩展性好。
```

---

## 五、DeepSeek 在哪里用（当面试官问 LLM 集成）

```
DeepSeek 在三个地方使用，都有开关控制：

1. Reply Polisher（LLM_ENABLE_REPLY_POLISH）
   - 模板回复生成后 → DeepSeek 润色 → Safety 检查 → 使用
   - 失败或不安全 → 回退模板

2. RAG Answer（LLM_ENABLE_RAG_ANSWER）
   - 基于检索到的文档 chunks 生成自然回答
   - 必须带 source_file 引用

3. Semantic Parser（LLM_ENABLE_SEMANTIC_PARSER）
   - 理解自然表达，输出结构化 JSON
   - Code 校验后再使用

所有 LLM 功能默认关闭，只有配置了才会启用。
```

---

## 六、RAG 在哪里用（当面试官问检索增强）

```
RAG 用于非结构化文档——售后政策、保养说明、FAQ。
数据是 Markdown 文件，切片后用 TF-IDF 做相似度检索。

检索到的 chunks 包含 source_file 和 score，
DeepSeek 基于 evidence 生成回答，如果没有证据就不编造。

当前用 TF-IDF，后续可以升级 Chroma/FAISS + embedding。
```

---

## 七、Structured + RAG 为什么混合（高频问题）

```
结构化查询和 RAG 各有各的用途：

结构化（products.json）：
  尺码、价格、颜色、材质
  → 直接读 JSON 字段，100% 准确
  → 不走 LLM，不编造

RAG（Markdown 文档）：
  退款政策、保养说明、FAQ
  → 适合非结构化文档
  → 检索 + 带来源引用

混合原因：
尺码用 RAG 检索可能错，直接读 JSON 是确定的。
政策用结构化不好存，RAG 更灵活。
两者互补，不是替代关系。
```

---

## 八、Semantic Parser 解决什么问题（加分项）

```
关键词规则只能识别"退款""尺码"这些硬词。
但用户会说"那个遮阳帽不错"、"第二个怎么样"——规则匹配不了。

Semantic Parser 让 LLM 理解自然表达，输出结构化 JSON：
{
  "intent": "product_question",
  "explicit_product": "可折叠遮阳帽",
  "query_type": "general",
  "confidence": 0.85
}

然后 Code 校验这个输出——confidence 够不够、
商品存在不存在、是不是把退款意图降级了——
校验通过才用，不通过就 fallback 到规则。
```

---

## 九、Policy 为什么不能交给 LLM（必考）

```
三个原因：

1. 可控性
   LLM 可能被 prompt injection 绕过，
   写在代码里的规则绕不过。

2. 可测试性
   decide_refund_action(1) → "retention"，每次一样。
   LLM 相同输入可能不同输出，没法单元测试。

3. 可追溯性
   policy_decision 存在 state 和 SQLite 里。
   LLM 输出不会自动记录，出了问题查不了。
```

---

## 十、Docker 一键启动为什么加分

```
docker compose up --build

一条命令就能跑起来，不需要配 Python 环境、Node 环境。
面试官也能自己跑起来体验。

也是工程化能力的体现——不只是写代码，
还考虑了别人怎么用你的项目。
```

---

## 十一、当前项目局限（诚实面）

```
1. RAG 还是 TF-IDF，精度不如 embedding 检索
2. 没有流式输出，用户等整个请求结束才看到回复
3. 商品数据是 JSON 文件，没有管理后台
4. 单 Agent 线性流程，不支持多 Agent 并行
5. 不是生产级 SaaS，没有用户认证和权限
```

---

## 十二、后续可扩展方向

```
1. RAG 升级 Chroma/FAISS + sentence-transformers
2. 流式输出 SSE/WebSocket
3. Docker Compose → Kubernetes
4. 多 Agent（Supervisor + 子 Agent）
5. 接入真实订单 API 和物流 API
6. 数据看板和客服质检后台
```
