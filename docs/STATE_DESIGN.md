# 状态设计文档 — CustomerServiceState

> **Phase 2.1 · 设计文档**
> 本文档只做设计讨论，不涉及代码实现。

---

## 一、为什么需要统一 State

### LangGraph 里的 State 是什么

LangGraph 的核心概念是 **StateGraph**。整个客服 Agent 的运行过程，就是数据在一个"图"里流转。而 **State（状态）** 就是图中每个节点之间传递的"数据包"。

用一个类比来理解：

```
传统方式（没有统一 State）：
    节点A → 自己记一笔数据
    节点B → 自己另记一笔数据
    节点C → 不知道找谁要数据
    → 混乱

Agent Harness 方式（有统一 State）：
    节点A → 写入 State
    节点B → 从 State 读取 → 写入 State
    节点C → 从 State 读取 → 写入 State
    → 有序
```

### 为什么不能各写各的

如果每个节点各自维护自己的变量，会出现以下问题：

1. **数据孤岛** — 节点 A 分析完意图，节点 B 不知道去哪里拿结果
2. **命名冲突** — 不同的人写不同的节点，用了不同的变量名表示同一件事
3. **难以调试** — 出问题时不知道数据在哪个环节丢失或出错
4. **无法回放** — 没有一个完整的数据快照，无法复现问题

### State 的核心作用

State 决定了后续所有模块（Node、Edge、Skill、Policy）怎么协作：

| 模块 | 和 State 的关系 |
|------|----------------|
| **Node（节点）** | 从 State 读输入，处理后写回 State |
| **Edge（边）** | 读取 State 中的字段，决定走哪条路 |
| **Skill（技能）** | 从 State 获取上下文，执行业务操作 |
| **Policy（策略）** | 从 State 读取业务数据，做出决策 |
| **Log（日志）** | 记录 State 每一步的变化 |

**一句话总结：State 设计混乱，后续代码一定混乱。State 设计清晰，后续开发事半功倍。**

---

## 二、CustomerServiceState 的职责

`CustomerServiceState` 是本项目中唯一的状态类，它负责承载客服流程中**所有**需要传递的数据。

具体来说，它承载以下内容：

| 职责 | 说明 |
|------|------|
| **用户输入** | 用户说了什么文本（user_message） |
| **图片输入** | 用户发了什么图片（URL 或 base64） |
| **输入类型** | 当前输入是纯文本、纯图片、还是图文混合 |
| **文本分析结果** | LLM 对用户文本的分析 |
| **图文分析结果** | LLM 对用户文本+图片的综合分析 |
| **意图识别结果** | 用户想做什么（咨询、退款、投诉……） |
| **情绪识别结果** | 用户当前情绪状态和评分 |
| **客户阶段** | 用户在客服流程中处于哪个阶段 |
| **路由结果** | 应该调用哪个 Skill |
| **Skill 执行结果** | Skill 执行后返回了什么数据 |
| **Policy 决策结果** | 业务规则做出的决策（如挽留/退款） |
| **转人工判断** | 是否需要转人工，以及原因 |
| **最终回复** | Agent 生成的回复文本 |
| **日志和错误** | 每一步的执行记录和异常信息 |

---

## 三、字段分组设计

按照职责相近的原则，所有字段分为 7 组：

### A. 会话输入字段

```
session_id       — 会话唯一标识
user_message     — 用户输入的文本
image_url        — 用户上传的图片 URL
image_base64     — 用户上传的图片 base64 编码
```

### B. 输入类型判断字段

```
modality         — 输入模态类型
```

### C. 分析结果字段

```
text_analysis         — 文本分析结果
multimodal_analysis   — 图文多模态分析结果
intent                — 用户意图分类
intent_confidence     — 意图置信度
emotion               — 用户情绪标签
emotion_score         — 用户情绪评分
customer_stage        — 客户所处阶段
```

### D. 路由和执行字段

```
selected_skill    — 选中要调用的技能
skill_result      — 技能执行结果
```

### E. 业务规则字段

```
policy_decision   — 策略决策结果
need_human        — 是否需要转人工
human_reason      — 转人工的原因
```

### F. 输出字段

```
reply             — 客服回复文本
```

### G. 工程观测字段

```
logs              — 节点执行日志列表
errors            — 错误信息列表
```

### 分组关系图

```
用户输入
  │
  ├─→ A. 会话输入（user_message, image_url, ...）
  │
  ▼
输入判断
  │
  ├─→ B. 模态判断（modality）
  │
  ▼
分析阶段
  │
  ├─→ C. 分析结果（intent, emotion, customer_stage, ...）
  │
  ▼
路由执行
  │
  ├─→ D. 路由和执行（selected_skill, skill_result）
  │
  ▼
规则判断
  │
  ├─→ E. 业务规则（policy_decision, need_human, ...）
  │
  ▼
输出
  │
  ├─→ F. 回复（reply）
  │
  ▼
观测
  │
  └─→ G. 日志错误（logs, errors）— 贯穿始终
```

---

## 四、每个字段的详细说明

### A. 会话输入字段

| 字段名 | 类型 | 默认值 | 写入节点 | 读取节点 | 为什么需要 |
|--------|------|--------|----------|----------|------------|
| `session_id` | `str` | `""` | 入口节点 | 所有节点 | 唯一标识一个客服会话，用于日志追踪和会话恢复 |
| `user_message` | `str` | `""` | 入口节点 | analyze 系列节点、skill 节点 | 保存用户输入的文本内容，所有分析都基于此字段 |
| `image_url` | `Optional[str]` | `None` | 入口节点 | decide_modality 节点、analyze_multimodal 节点 | 记录用户上传图片的 URL 地址 |
| `image_base64` | `Optional[str]` | `None` | 入口节点 | analyze_multimodal 节点 | 记录图片的 base64 编码，用于多模态分析 |

### B. 输入类型判断字段

| 字段名 | 类型 | 默认值 | 写入节点 | 读取节点 | 为什么需要 |
|--------|------|--------|----------|----------|------------|
| `modality` | `str` | `"unknown"` | decide_modality 节点 | route 节点、analyze_text 节点 | 决定后续走纯文本分析还是多模态分析路径。取值：`"text_only"`、`"image_only"`、`"text_with_image"`、`"unknown"` |

### C. 分析结果字段

| 字段名 | 类型 | 默认值 | 写入节点 | 读取节点 | 为什么需要 |
|--------|------|--------|----------|----------|------------|
| `text_analysis` | `Optional[str]` | `None` | analyze_text 节点 | classify_intent 节点、classify_emotion 节点 | LLM 对用户文本的分析摘要，包含对用户问题的理解和关键信息提取 |
| `multimodal_analysis` | `Optional[str]` | `None` | analyze_multimodal 节点 | classify_intent 节点、classify_emotion 节点 | LLM 对文本+图片的综合分析结果。用户先发文字后发图片时，需要结合上轮文字分析 |
| `intent` | `Optional[str]` | `None` | classify_intent 节点 | route_to_skill 节点、escalation_policy 节点、generate_reply 节点 | 路由决策的核心输入，决定调用哪个 skill。取值：`"product_question"`、`"recommendation"`、`"logistics_question"`、`"refund_request"`、`"exchange_request"`、`"complaint"`、`"human_request"`、`"smalltalk"` |
| `intent_confidence` | `float` | `0.0` | classify_intent 节点 | route_to_skill 节点 | 反映 LLM 对意图判断的把握程度，置信度过低时可走兜底流程 |
| `emotion` | `str` | `"neutral"` | classify_emotion 节点 | escalation_policy 节点、generate_reply 节点 | 用户情绪标签，帮助客服选择合适的语气回复。取值：`"neutral"`、`"anxious"`、`"angry"`、`"disappointed"`、`"urgent"` |
| `emotion_score` | `float` | `0.0` | classify_emotion 节点 | escalation_policy 节点 | 0.0~1.0 的连续值，用于触发转人工规则（>0.85 转人工） |
| `customer_stage` | `str` | `"unknown"` | classify_stage 节点 | route_to_skill 节点、generate_reply 节点 | 了解用户在客服流程中的位置，帮助选择合适的话术。取值：`"pre_sale"`、`"in_sale"`、`"after_sale"`、`"unknown"` |

### D. 路由和执行字段

| 字段名 | 类型 | 默认值 | 写入节点 | 读取节点 | 为什么需要 |
|--------|------|--------|----------|----------|------------|
| `selected_skill` | `Optional[str]` | `None` | route_to_skill 节点 | 各 skill 节点、generate_reply 节点 | 根据 intent 路由到的目标 skill 名称。LangGraph 根据此字段决定调用哪个 skill |
| `skill_result` | `Optional[Any]` | `None` | 各个 skill 节点 | generate_reply 节点、policy 节点 | skill 执行后的返回数据，如退款结果、查询结果等。generate_reply 据此生成回复文本 |

### E. 业务规则字段

| 字段名 | 类型 | 默认值 | 写入节点 | 读取节点 | 为什么需要 |
|--------|------|--------|----------|----------|------------|
| `policy_decision` | `Optional[str]` | `None` | 各 policy 函数 | 各 skill 节点、generate_reply 节点 | 业务规则做出的决策。如退款 policy 输出 `"retention"`、`"refund_workflow"`、`"direct_refund_or_human_confirm"`。State **只保存决策结果**，不保存复杂规则本身 |
| `need_human` | `bool` | `False` | escalation_check 节点、escalation_policy 函数 | generate_reply 节点、graph 边 | 控制是否需要走转人工流程。`True` 时生成转人工提示 |
| `human_reason` | `Optional[str]` | `None` | escalation_check 节点、escalation_policy 函数 | generate_reply 节点、save_log 节点 | 记录转人工的原因，用于向用户和人工客服说明情况 |

### F. 输出字段

| 字段名 | 类型 | 默认值 | 写入节点 | 读取节点 | 为什么需要 |
|--------|------|--------|----------|----------|------------|
| `reply` | `Optional[str]` | `None` | generate_reply 节点 | 输出节点、save_log 节点 | Agent 最终回复文本，是客服流程的输出结果 |

### G. 工程观测字段

| 字段名 | 类型 | 默认值 | 写入节点 | 读取节点 | 为什么需要 |
|--------|------|--------|----------|----------|------------|
| `logs` | `List[dict]` | `[]` | 每个节点（通过 save_log 统一收集） | save_log 节点、调试工具 | 记录每个节点的执行过程，包括节点名、输入摘要、输出摘要、耗时。用于调试、测试和回放 |
| `errors` | `List[str]` | `[]` | 每个节点（执行出错时） | escalation_policy 节点、调试工具 | 记录节点执行失败和兜底信息。errors 不为空时会触发转人工 |

---

## 五、LLM 和代码职责边界

### 核心原则

> **LLM 负责"理解"，代码负责"决策"和"执行"。**

这个原则体现在 State 字段的写入职责划分上：

### LLM / mock LLM 可以生成（分析类字段）

```
text_analysis         — 理解用户文本内容
multimodal_analysis   — 理解用户图文内容
intent                — 判断用户意图
intent_confidence     — 给出意图置信度
emotion               — 识别用户情绪
emotion_score         — 量化情绪程度
customer_stage        — 判断客户阶段
reply                 — 生成回复文本
```

这些字段的特点是：**需要"理解"能力**。LLM 擅长从自然语言中提取信息，所以这些字段交给 LLM。

### 代码 / policy 必须生成（决策和执行类字段）

```
modality              — 根据输入字段判断（有图/无图）
selected_skill        — 根据 intent 路由（if-else 或 dict 映射）
skill_result          — 调用 mock tool 执行
policy_decision       — 根据 refund_count 等规则决策
need_human            — 根据 emotion_score、intent 等规则决策
human_reason          — 根据规则生成原因
logs                  — 自动记录
errors                — 自动捕获
```

这些字段的特点是：**需要"确定性决策"或"外部执行"**。代码比 LLM 更可靠、更可控。

### 两个重要的反面例子

#### 反面例子 1：退款规则写进 prompt

```
❌ 错误做法：
  system_prompt = "如果用户第一次要求退款，先挽留；第二次才退款……"
  → LLM 可能忽略规则、被 prompt injection 绕过

✅ 正确做法：
  LLM 只输出 intent = "refund_request"
  refund_policy.py 根据 refund_count 判断走挽留还是退款
  policy_decision = refund_policy.decide_refund_action(refund_count)
```

#### 反面例子 2：LLM 决定是否转人工

```
❌ 错误做法：
  prompt 里写 "如果用户很生气，就转人工"
  → LLM 对"很生气"的理解不一致，有时转有时不转

✅ 正确做法：
  LLM 输出 emotion_score = 0.9
  escalation_policy.py 判断 if emotion_score > 0.85 → need_human = True
```

### 职责边界图示

```
┌──────────────────────────────────────────┐
│          用户输入到达                       │
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────┐
│  代码：modality = decide_modality(...)    │  ← 代码判断
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────┐
│  LLM：intent, emotion, customer_stage     │  ← LLM 理解
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────┐
│  代码：selected_skill = route_by_intent() │  ← 代码路由
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────┐
│  代码：policy_decision = refund_policy()  │  ← Policy 决策
│  代码：need_human = escalation_policy()   │
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────┐
│  LLM：reply = generate_reply(...)         │  ← LLM 组织语言
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────┐
│  代码：logs, errors 自动记录              │  ← 代码观测
└─────────────────────────────────────────┘
```

---

## 六、为什么 State 里要有 logs 和 errors

### logs — 节点执行日志

```python
state.logs = [
    {
        "node": "parse_input",
        "input": "用户说：我的快递怎么还没到",
        "output": "解析完成，检测到文本输入",
        "timestamp": "2024-01-01 12:00:01",
    },
    {
        "node": "analyze_text",
        "input": "用户说：我的快递怎么还没到",
        "output": "意图=logistics_question，情绪=anxious",
        "timestamp": "2024-01-01 12:00:02",
    },
]
```

`logs` 的作用：
- **可观测** — 随时查看当前处理到哪一步了
- **可调试** — 出问题时可以逐节点回放，找到哪一步出问题
- **可测试** — 测试用例可以验证每个节点是否按预期执行
- **可审计** — 后续接入真实环境时，可用于客服质量分析

### errors — 错误记录

```python
state.errors = [
    "analyze_multimodal 节点执行失败：图片格式不支持",
    "refund_skill 执行异常：退款接口超时",
]
```

`errors` 的作用：
- **兜底触发** — 当 errors 不为空时，escalation_policy 自动触发转人工
- **不可让 LLM 自行消化错误** — 错误必须记录在 state 中，由 policy 决定如何处理
- **问题追踪** — 每个错误都有记录，不会静默丢失

### 为什么在 State 里而不是外部文件

- **实时性** — 外部日志文件无法被正在运行的节点实时读取
- **完整性** — State 快照包含完整日志，一次导出即可复现全过程
- **简单性** — 第一版不需要引入额外的日志系统，state 中的 list 就够了

---

## 七、TypedDict 和 Pydantic 的选择建议

### TypedDict

```python
from typing import TypedDict, Optional

class CustomerServiceState(TypedDict):
    session_id: str
    user_message: str
    intent: Optional[str]
    # ...
```

优点：
- LangGraph 原生支持 dict 类型的状态流转
- 定义简单，初学者容易理解
- 不需要额外依赖
- 序列化/反序列化方便

缺点：
- 没有运行时校验（不会自动报类型错误）
- 没有默认值机制（需要手动在创建时补齐）
- 嵌套结构处理不够优雅

### Pydantic BaseModel

```python
from pydantic import BaseModel, Field

class CustomerServiceState(BaseModel):
    session_id: str = Field(default="")
    user_message: str = Field(default="")
    intent: Optional[str] = None
    # ...
```

优点：
- 运行时校验（类型错误及时报错）
- 支持默认值
- 嵌套模型支持好
- 商业级项目更规范

缺点：
- LangGraph 使用 dict 流转时可能需要序列化转换
- 额外依赖（pydantic）
- 定义相对复杂

### 第一版建议：使用 TypedDict

| 维度 | TypedDict | Pydantic |
|------|-----------|----------|
| 学习成本 | 低 | 中 |
| 类型校验 | 静态 | 运行时 |
| 默认值 | 手动 | 自动 |
| 序列化 | 原生 dict | 需 .dict() |
| LangGraph 适配 | 原生 | 需配置 |
| 适合阶段 | V4-lite | 商业版 |

**本项目 V4-lite 第一版使用 TypedDict**，原因：

1. **最小可运行** — 不需要引入额外依赖和配置
2. **易理解** — 初学者看到的就是一个清晰的 dict 结构
3. **贴近 LangGraph** — LangGraph 的 state 流转本来就是 dict 风格
4. **够用** — 第一版的校验需求不复杂，手动补齐默认值即可

如果后续商业版本需要更强的校验，可以轻松迁移到 Pydantic，字段结构不变。

---

## 八、初始 State JSON 示例

假设用户输入：
```
session_id = "demo-session-001"
user_message = "我的快递怎么还没到"
image_url = None
image_base64 = None
```

初始 State 如下：

```json
{
  "session_id": "demo-session-001",
  "user_message": "我的快递怎么还没到",
  "image_url": null,
  "image_base64": null,

  "modality": "unknown",

  "text_analysis": null,
  "multimodal_analysis": null,
  "intent": null,
  "intent_confidence": 0.0,
  "emotion": "neutral",
  "emotion_score": 0.0,
  "customer_stage": "unknown",

  "selected_skill": null,
  "skill_result": null,

  "policy_decision": null,
  "need_human": false,
  "human_reason": null,

  "reply": null,

  "logs": [],
  "errors": []
}
```

特点：
- 所有分析结果都是 `null` 或默认值
- `modality = "unknown"` 表示尚未判断输入类型
- `logs` 和 `errors` 初始为空列表
- 所有 bool 字段默认为 `false`

---

## 九、执行后 State JSON 示例

假设用户输入：
```
user_message = "质量太差了我要退款"
```

经过完整客服流程处理后，State 如下：

```json
{
  "session_id": "demo-session-001",
  "user_message": "质量太差了我要退款",
  "image_url": null,
  "image_base64": null,

  "modality": "text_only",

  "text_analysis": "用户对商品质量不满意，明确表示要申请退款。核心诉求是退款，属于售后问题。",
  "multimodal_analysis": null,
  "intent": "refund_request",
  "intent_confidence": 0.92,
  "emotion": "angry",
  "emotion_score": 0.82,
  "customer_stage": "after_sale",

  "selected_skill": "refund_skill",
  "skill_result": {
    "status": "completed",
    "action": "retention",
    "message": "查询到用户首次退款请求，已执行挽留流程"
  },

  "policy_decision": "retention",
  "need_human": false,
  "human_reason": null,

  "reply": "您好，非常抱歉给您带来不好的体验。我看了一下，您这是第一次申请退款，您方便告诉我具体是什么问题吗？我们先帮您看看有没有其他解决方案。",

  "logs": [
    {
      "node": "parse_input",
      "summary": "解析用户输入",
      "timestamp": "2024-01-01 12:00:00"
    },
    {
      "node": "decide_modality",
      "summary": "判断为 text_only",
      "timestamp": "2024-01-01 12:00:00"
    },
    {
      "node": "analyze_text",
      "summary": "文本分析完成",
      "timestamp": "2024-01-01 12:00:01"
    },
    {
      "node": "classify_intent",
      "summary": "意图=refund_request, 置信度=0.92",
      "timestamp": "2024-01-01 12:00:01"
    },
    {
      "node": "classify_emotion",
      "summary": "情绪=angry, 评分=0.82",
      "timestamp": "2024-01-01 12:00:02"
    },
    {
      "node": "classify_stage",
      "summary": "阶段=after_sale",
      "timestamp": "2024-01-01 12:00:02"
    },
    {
      "node": "route_to_skill",
      "summary": "路由到 refund_skill",
      "timestamp": "2024-01-01 12:00:02"
    },
    {
      "node": "refund_policy",
      "summary": "退款策略=retention（首次退款，挽留）",
      "timestamp": "2024-01-01 12:00:03"
    },
    {
      "node": "refund_skill",
      "summary": "执行挽留流程完成",
      "timestamp": "2024-01-01 12:00:03"
    },
    {
      "node": "escalation_check",
      "summary": "emotion_score=0.82 <= 0.85，不转人工",
      "timestamp": "2024-01-01 12:00:03"
    },
    {
      "node": "generate_reply",
      "summary": "已生成挽留回复",
      "timestamp": "2024-01-01 12:00:04"
    }
  ],

  "errors": []
}
```

从这个示例可以看出：

1. **职责清晰** — `intent`, `emotion` 由 LLM 分析得到；`policy_decision` 由代码规则判断
2. **路径可见** — logs 完整记录了每一次节点执行，可以追溯每一步
3. **决策透明** — `escalation_check` 日志说明为什么没转人工（0.82 ≤ 0.85）
4. **业务规则独立** — `policy_decision = "retention"` 由 `refund_policy.py` 决定，不来自 LLM

---

## 十、验收标准

Phase 2.1 设计阶段完成的验收标准：

| # | 验收项 | 状态 |
|---|--------|------|
| 1 | docs/STATE_DESIGN.md 已创建 | ✅ |
| 2 | State 字段分组清晰（7 组：会话输入、模态判断、分析结果、路由执行、业务规则、输出、观测） | ✅ |
| 3 | 每个字段说明了类型、默认值、写入节点、读取节点、存在原因 | ✅ |
| 4 | 明确区分 LLM 职责和代码/policy 职责 | ✅ |
| 5 | 有初始 state JSON 示例 | ✅ |
| 6 | 有执行后 state JSON 示例 | ✅ |
| 7 | 没有修改 app/ 目录（包括 app/main.py） | ✅ |
| 8 | 没有写业务代码（纯设计文档） | ✅ |
| 9 | 文档用中文，适合初学者理解 | ✅ |
| 10 | 没有过度设计 | ✅ |

---

> **下一阶段建议**：进入 Phase 2.2，根据本文档的字段设计实现 `CustomerServiceState`（TypedDict 版本）。
