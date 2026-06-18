# Demo 录屏脚本 — 2-3 分钟

> 目标：清晰展示 LangGraph 电商客服 Agent Harness 的核心能力。
> 时长：2-3 分钟。语气：自信、简洁。

---

## 0:00 — 开场（15 秒）

```
大家好，今天给大家演示一个我做的项目：
LangGraph 电商客服 Agent Harness。

它不是普通的 Chatbot，而是一个 Agent 运行框架——
LLM 只负责理解和表达，退款、转人工等关键决策由代码控制。
```

屏幕：项目 README 或首页

---

## 0:15 — 打开页面（15 秒）

```
我们先启动项目。
Docker Compose 一键启动，不需要配环境。
```

屏幕：终端执行 `docker compose up --build`（快进或已启动）

```
前端是 Next.js，后端是 FastAPI + LangGraph。
这是聊天页面，左侧是快速体验按钮，右侧是 Agent Trace 分析面板。
```

屏幕：http://localhost:3001 页面

---

## 0:30 — 商品推荐 + DeepSeek 润色（20 秒）

```
先点「售前推荐」。
Agent 识别为 recommendation 意图，
推荐了三款商品——防晒衣、运动外套、遮阳帽。
右侧能看到 intent、skill、情绪分析。
回复经过了 DeepSeek 润色，比模板更自然。
```

屏幕：点击"售前推荐"→ 展示回复 + Agent Trace

---

## 0:50 — 多轮上下文 + Semantic Parser（25 秒）

```
接着我输入「那个遮阳帽不错」。
这里用了 LLM Semantic Parser 来理解自然表达——
规则匹配只能识别"退款""尺码"这些硬词，
但 Semantic Parser 能理解"那个"指代上一轮的遮阳帽，
explicit_product 被识别为可折叠遮阳帽。
回复围绕遮阳帽继续介绍。
```

屏幕：输入"那个遮阳帽不错"→ 展示 Trace 中 intent_source=llm、explicit_product

---

## 1:15 — RAG 政策问答（20 秒）

```
问一个售后政策问题：「超过7天还能退吗」。
系统走的是 RAG 知识库检索，
从本地 Markdown 文档中匹配到 refund_policy.md 的相关内容，
回复带来源标注。右侧 Trace 能看到 evidence 和 source_file。
```

屏幕：输入"超过7天还能退吗"→ 展示 RAG evidence 卡片

---

## 1:35 — 退款安全边界（20 秒）

```
然后测试安全边界：「质量太差了我要退款」。
注意右侧 Trace——selected_skill 是 refund_skill，
policy_decision 是 retention（首次退款挽留）。
退款决策由 refund_policy.py 代码控制，LLM 不参与。
即使 DeepSeek 出了 bug，也不会自动退款。
```

屏幕：输入"质量太差了我要退款"→ 展示 refund_skill + retention

---

## 1:55 — 总结（30 秒）

```
以上就是这个项目的核心能力：

1. 混合知识库：结构化商品 JSON + RAG 文档检索
2. LLM Semantic Parser：理解自然表达
3. DeepSeek 回复润色：更自然的客服语气
4. Policy 安全边界：退款、转人工由代码控制
5. Docker 一键启动：docker compose up 就能跑
6. Agent Trace：每个节点的 intent、skill、evidence 都可查看

项目已开源，GitHub 地址在 README 里。
谢谢！
```

---

## 附录：录屏准备提示

| 准备工作 | 说明 |
|---------|------|
| 提前启动 Docker | `docker compose up --build` |
| 准备好演示场景 | 按顺序操作，不要卡顿 |
| 右侧 Trace 面板 | 确保 return_full_state=true |
| 录屏工具 | 推荐 OBS Studio 或系统自带 QuickTime |
| 时长控制 | 语速适中，总时长控制在 3 分钟内 |
