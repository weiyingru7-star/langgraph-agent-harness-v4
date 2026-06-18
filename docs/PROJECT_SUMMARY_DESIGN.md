# 项目收尾设计 — PROJECT_SUMMARY_DESIGN

> **Phase 8.1 · 设计文档**
> 本文档规划 README.md 的内容结构和项目展示方式。

---

## 一、项目一句话介绍

> 基于 Python + LangGraph 构建的电商客服 Agent Harness V4-lite，支持文本、图片、图文输入，具备意图识别、情绪识别、客户阶段判断、Skill 路由、Policy 规则、Mock Tool、多模态路由、回复生成和测试验证。

---

## 二、项目目标

### 这不是什么

```
❌ 不是 LLM Prompt Demo
   把所有逻辑塞进 prompt，LLM 决定一切
   不可控、不可观测、不可测试

❌ 不是简单 RAG 客服机器人
   向量检索 + LLM 拼接回复
   缺乏流程控制

❌ 不是 LangGraph 官方教程复制
   是自己从零搭建的 Agent Harness 学习项目
```

### 这是什么

```
✅ Agent Harness 学习项目

   LLM 只负责"理解"（意图/情绪/阶段）
   LangGraph 负责"流转"（StateGraph 节点）
   Skill/Tool/Policy 负责"执行"（业务逻辑）
   Logs/Tests 负责"验证"（可观测/可测试）

   核心工程化思维：
     可控 → 每个节点可独立测试
     可测 → 60 个 pytest 覆盖全路径
     可追踪 → 每步执行写入 logs
     可扩展 → 新增 skill 只需加一个文件
```

---

## 三、技术栈

| 技术 | 用途 | 版本 |
|------|------|------|
| Python | 运行时 | 3.13 |
| LangGraph | 状态图框架 | 1.x |
| langchain-core | 基础组件 | 1.x |
| Pydantic / TypedDict | 状态模型 | — |
| pytest | 测试框架 | — |
| Claude Code + Superpowers | AI 辅助开发 | — |

**运行环境：**

```bash
# 虚拟环境
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 运行
.venv/bin/python -m app.main

# 测试
.venv/bin/python -m pytest
```

---

## 四、核心架构

### 架构分层

```
┌─────────────────────────────────────────────────────┐
│                     State                            │
│           CustomerServiceState                       │
│     (所有节点共享的 TypedDict 数据包)                  │
├─────────────────────────────────────────────────────┤
│                     Nodes                            │
│   parse_input → decide_modality → analyze_text       │
│   → classify_intent → classify_emotion               │
│   → classify_stage → route_to_skill                  │
│   → escalation_check → generate_reply → save_log     │
├─────────────────────────────────────────────────────┤
│                     Skills                           │
│   product_qa / recommendation / logistics            │
│   / refund / exchange / complaint / human             │
├─────────────────────────────────────────────────────┤
│                     Tools                            │
│   mock_product_tool / mock_order_tool                 │
│   / mock_multimodal_tool                              │
├─────────────────────────────────────────────────────┤
│                     Policies                         │
│   refund_policy / escalation_policy                   │
├─────────────────────────────────────────────────────┤
│                     Memory                           │
│   session-based conversation memory (in-memory)      │
├─────────────────────────────────────────────────────┤
│                     Logs / Errors                    │
│   每个节点写入 logs，出错时触发转人工                 │
├─────────────────────────────────────────────────────┤
│                     Tests                            │
│   60 个测试覆盖所有路径                               │
└─────────────────────────────────────────────────────┘
```

### 各层职责

| 层次 | 职责 | 不允许做什么 |
|------|------|-------------|
| **LLM** | 理解用户意图、分类、路由 | 不直接执行业务动作、不直接操作工具 |
| **LangGraph** | 任务流转、状态管理 | 不包含业务逻辑 |
| **Skill** | 封装客服业务能力 | 不直接调用外部系统 |
| **Tool** | 访问外部系统或 mock 外部系统 | 不做业务判断 |
| **Policy** | 业务规则判断 | 不参与对话生成 |
| **Memory** | 保存会话上下文 | 不做决策 |
| **Logs** | 记录每一步状态变化 | 无 |
| **Tests** | 验证每条客服路径是否正确 | 无 |

---

## 五、当前完整流程

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

## 六、支持的场景

| # | 场景 | 输入示例 | 流程路径 |
|---|------|---------|---------|
| 1 | **物流查询** | "我的快递怎么还没到" | text → logistics_skill → 返回物流信息 |
| 2 | **商品咨询** | "这个衣服是什么材质" | text → product_qa_skill → 返回商品信息 |
| 3 | **售前推荐** | "推荐一款好用的手机" | text → recommendation_skill → 返回推荐商品 |
| 4 | **退款请求** | "质量太差了我要退款" | text → refund_skill → policy_decision |
| 5 | **换货请求** | "我要换个尺码" | text → exchange_skill → 换货流程 |
| 6 | **投诉** | "你们这个太垃圾了，我要投诉" | text → complaint_skill → 转人工 |
| 7 | **转人工** | "我要人工，太生气了" | text → human_skill → need_human=True |
| 8 | **闲聊兜底** | "你好，在吗" | text → smalltalk_fallback |
| 9 | **纯图片追问** | (只发图片，无文字) | image → 追问"请问您想咨询什么" |
| 10 | **图文多模态** | "这个破了能退吗" + 图片 | text_with_image → analyze_multimodal |
| 11 | **先文字后图片** | 先"这个怎么安装"，后发图片 | memory → 图文合并分析 |

---

## 七、为什么这是 Agent Harness，不是 Prompt Demo

### Prompt Demo 的做法

```
用户输入 → LLM（prompt 中写了所有规则）→ 回复
```

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
- **外部能力通过 `mock_product_tool` / `mock_order_tool`**，不让 LLM 直接访问
- **每一步写入 `state["logs"]`**，可回放、可调试
- **pytest 覆盖全路径**，60 个测试验证每个节点行为

---

## 八、运行方式

```bash
# 克隆项目
git clone <repo-url>
cd langgraph-agent-harness-v4

# 创建虚拟环境
python3 -m venv .venv

# 安装依赖
.venv/bin/pip install -r requirements.txt

# 运行主程序（展示 8 个客服场景）
.venv/bin/python -m app.main

# 运行全部测试
.venv/bin/python -m pytest -v

# 运行特定测试
.venv/bin/python -m pytest app/tests/test_skills_policies.py -v
```

---

## 九、演示样例

### Demo 1：物流查询

```bash
.venv/bin/python -m app.main
```

```
输入： "我的快递怎么还没到"

modality       = text_only
selected_skill = logistics_skill
reply          = "感谢您的耐心等待，我来帮您查看一下物流信息。
                  您的快递已发货，单号 SF1234567890……"
```

### Demo 2：退款挽留

```
输入： "质量太差了我要退款"

intent          = refund_request
policy_decision = retention
need_human      = true（emotion 0.9 → 触发转人工）
reply           = "正在为您转接人工客服……"
```

### Demo 3：商品咨询

```
输入： "这个衣服是什么材质"

selected_skill = product_qa_skill
reply          = "商品名称：经典款运动鞋 | 材质：透气网面 + EVA 鞋底……"
```

### Demo 4：转人工

```
输入： "气死了，我要人工"

intent   = human_request
need_human = true
reply    = "正在为您转接人工客服……"
```

### Demo 5：投诉

```
输入： "你们这个太垃圾了，我要投诉"

selected_skill = complaint_skill
need_human     = true
reply          = "非常抱歉……已记录投诉信息……转接人工客服"
```

### Demo 6：闲聊

```
输入： "你好，在吗"

selected_skill = None（smalltalk_fallback）
reply          = "您好，我在的。请问有什么可以帮您？"
```

### Demo 7：纯图片追问

```
输入： (image_url 图片，无文字)

modality       = image_only
selected_skill = None
reply          = "我看到您发了一张图片，请问您想咨询这张图片里的什么问题？
                  比如质量、材质、安装、售后还是价格？"
```

### Demo 8：图文多模态

```
输入： "这个破了能退吗" + 破损图片

modality = text_with_image
multimodal_analysis = {"visible_issue": "疑似商品破损……"}
selected_skill = refund_skill
```

### Demo 9：先文字后图片

```
第一轮： "这个怎么安装"
第二轮： (安装图片)

第二轮 modality = text_with_image（memory 合并）
第二轮 intent   = product_question
```

---

## 十、项目边界

当前 V4-lite 第一版**没有接**以下真实能力：

| 不做 | 原因 |
|------|------|
| **真实 LLM** | 第一版用关键词规则 + 模板回复 |
| **真实多模态模型** | 第一版使用 mock |
| **真实电商 API** | 全部 mock 数据 |
| **数据库** | 数据在 State 中流转 |
| **Dify / RAG 知识库** | 后续可接入 |
| **飞书机器人** | 第一版 CLI 运行 |
| **n8n / 自动化** | 后续可接入 |
| **Redis** | 内存 dict 已够用 |
| **Docker 部署** | 后续可容器化 |
| **前端页面** | 第一版纯后端 |

---

## 十一、后续升级路线

| 阶段 | 升级内容 |
|------|---------|
| **短期** | 替换关键词规则为真实 LLM 调用 |
| **短期** | 替换 mock tool 为真实 API |
| **中期** | 接入 Dify / RAG 知识库 |
| **中期** | 接 FastAPI 提供 REST API |
| **中期** | 接前端页面（React / Vue） |
| **中期** | 接飞书机器人 |
| **中期** | 接 n8n 工单流程 |
| **中期** | 数据库持久化会话 |
| **长期** | Docker 容器化部署 |
| **长期** | 真实多模态模型接入 |
| **长期** | 多语言支持 |
| **长期** | A/B 测试框架 |

---

## 十二、Phase 8.2 README 实现边界

### 允许修改的文件

| 文件 | 操作 |
|------|------|
| `README.md` | **重写** — 根据本文档内容编写最终 README |

### 不得修改的文件

| 文件 | 原因 |
|------|------|
| `app/` | 业务代码已定稿 |
| `tests/` | 测试已定稿 |
| `docs/STATE_DESIGN.md` | 设计文档已定稿 |
| `docs/GRAPH_DESIGN.md` | 设计文档已定稿 |
| `docs/CLASSIFICATION_DESIGN.md` | 设计文档已定稿 |
| `docs/SKILL_POLICY_DESIGN.md` | 设计文档已定稿 |
| `docs/REPLY_DESIGN.md` | 设计文档已定稿 |
| `docs/MULTIMODAL_DESIGN.md` | 设计文档已定稿 |
| `docs/PROJECT_SUMMARY_DESIGN.md` | 本文档 |

---

## 十三、Phase 8.2 验收标准

| # | 验收项 | 验证方式 |
|---|--------|---------|
| 1 | README.md 能让别人看懂项目是什么 | 文档审查 |
| 2 | README.md 包含技术栈 | 文档审查 |
| 3 | README.md 包含架构图或分层说明 | 文档审查 |
| 4 | README.md 包含运行命令 | 执行验证 |
| 5 | README.md 包含测试命令 | 执行验证 |
| 6 | README.md 包含 demo 场景 | 文档审查 |
| 7 | README.md 解释 Agent Harness 和 Prompt Demo 的区别 | 文档审查 |
| 8 | README.md 说明当前边界和后续路线 | 文档审查 |
| 9 | 没有修改 app/ 目录 | git diff |
| 10 | `.venv/bin/python -m pytest` 仍然通过 | 直接运行 |

---

> **下一阶段建议**：进入 **Phase 8.2**，根据本文档重写 `README.md`。
