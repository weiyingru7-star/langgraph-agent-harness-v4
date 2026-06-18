# 最小 LangGraph 流程设计 — GRAPH_DESIGN

> **Phase 3.1 · 设计文档**
> 本文档只做设计讨论，不涉及代码实现。

---

## 一、为什么需要先做最小 LangGraph 流程

### 当前进展回顾

到 Phase 2.3 为止，我们已经完成了：

- `CustomerServiceState` 的定义（TypedDict）
- `create_initial_state()` 工厂函数
- 枚举常量（intent、emotion、modality、customer_stage）
- 单元测试覆盖

但这些代码**还没有运行在 LangGraph 中**。State 目前只是在 `main.py` 里手动创建并打印，没有经过任何节点处理。

### Phase 3.1 的核心目标

现在不急着做完整的客服 Agent，先回答一个更基础的问题：

> **State 能不能在 LangGraph 节点之间正常流转？**

具体来说，我们要验证：

1. LangGraph 的 `StateGraph` 能正确接收我们的 `CustomerServiceState`
2. 节点函数能正确从 State 读取数据，处理后写回 State
3. State 在经过多个节点后，字段被正确更新
4. `add_node` + `add_edge` 的基本机制能正常工作

### 为什么不能跳过这一步

如果直接做完整客服 Agent，遇到问题时会分不清：

- 是 State 定义的问题？
- 是 LangGraph 配置的问题？
- 是节点逻辑的问题？
- 还是 Policy / Skill 的问题？

先跑通 **START → Node → END** 的最小闭环，为后续复杂流程打下可靠基础。

---

## 二、Phase 3 的最小流程图

```
                    ┌─────────────┐
                    │    START    │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ parse_input │  接收用户输入，记录日志
                    └──────┬──────┘
                           │
                           ▼
                    ┌───────────────┐
                    │decide_modality│  判断输入模态（text/image/multimodal）
                    └───────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ analyze_text │  对文本内容做 mock 分析
                    └───────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  save_log   │  追加流程完成标记
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │     END     │
                    └─────────────┘
```

### 每一步的作用

| 步骤 | 做什么 | 为什么需要 |
|------|--------|------------|
| **parse_input** | 接收用户的输入，记录到 `logs` | 每一个流程都需要一个入口节点，负责接收和记录原始输入 |
| **decide_modality** | 判断是纯文本、纯图片还是图文混合 | 决定后续走哪条分析路径，这是条件路由的"前奏" |
| **analyze_text** | 对文本做分析摘要（第一版用 mock） | 验证文本分析类的字段是否能被正确写入 |
| **save_log** | 在 `logs` 中追加流程完成记录 | 确保 `logs` 字段在整个流程中被正确累积 |

**一句话总结：先让 State 在 4 个节点里完整走一圈，为后续加入真实逻辑铺路。**

---

## 三、节点职责设计

### 1. `parse_input` — 输入解析节点

**职责：**

- 接收初始 State
- 不做任何业务判断（不分析意图、不判断情绪）
- 在 `logs` 中追加 `parse_input` 执行记录
- 第一版只做日志记录，不修改输入字段

**读取字段：**

| 字段 | 读取目的 |
|------|----------|
| `session_id` | 记录当前处理的是哪个会话 |
| `user_message` | 记录用户输入的内容摘要 |
| `image_url` | 记录是否有图片输入 |
| `image_base64` | 记录图片信息（仅用于日志） |

**写入字段：**

| 字段 | 写入内容 |
|------|----------|
| `logs` | 追加一条执行记录，包含节点名、输入摘要、时间戳 |

**为什么需要这个节点：**

- 每个 Agent 流程都需要一个明确的入口
- 入口节点负责"接收"和"记录"，不负责"判断"
- 后续如果需要做输入校验（如空输入处理），可以在这里扩展

---

### 2. `decide_modality` — 模态判断节点

**职责：**

- 根据 `user_message` 和 `image_url`/`image_base64` 判断输入类型
- 这是一个 **纯代码判断**，不调用 LLM
- 在 `logs` 中追加 `decide_modality` 执行记录

**判断逻辑：**

```python
if user_message and (image_url or image_base64):
    modality = "text_with_image"
elif user_message:
    modality = "text_only"
elif image_url or image_base64:
    modality = "image_only"
else:
    modality = "unknown"
```

**读取字段：**

| 字段 | 读取目的 |
|------|----------|
| `user_message` | 判断用户是否输入了文字 |
| `image_url` | 判断用户是否上传了图片 |
| `image_base64` | 判断用户是否上传了图片（base64） |

**写入字段：**

| 字段 | 写入内容 |
|------|----------|
| `modality` | 取值为 `"text_only"` / `"image_only"` / `"text_with_image"` / `"unknown"` |
| `logs` | 追加一条执行记录 |

**为什么需要这个节点：**

- 后续分析路径取决于输入类型（纯文本 vs 多模态）
- 这是一个**纯函数**——输出完全由输入决定，没有副作用
- 体现了"代码负责确定性判断"的原则

---

### 3. `analyze_text` — 文本分析节点

**职责：**

- 对用户输入的文本做分析摘要
- **第一版不调用真实 LLM**，只做 mock 文本分析
- 如果 `modality` 是 `"image_only"`，则跳过文本分析
- 在 `logs` 中追加 `analyze_text` 执行记录

**判断逻辑：**

```python
if modality in ("text_only", "text_with_image") and user_message:
    text_analysis = f"用户输入了一段文本，内容是：{user_message}"
else:
    text_analysis = None
```

**读取字段：**

| 字段 | 读取目的 |
|------|----------|
| `user_message` | 获取用户输入的文本内容 |
| `modality` | 判断是否需要执行文本分析 |

**写入字段：**

| 字段 | 写入内容 |
|------|----------|
| `text_analysis` | 文本分析摘要字符串，或 `None` |
| `logs` | 追加一条执行记录 |

**为什么需要这个节点：**

- 验证"分析结果类字段"能否被正确写入
- 模拟 LLM 分析的流程位置，后续替换为真实 LLM 调用时，接口不变
- 体现了"LLM 负责理解"的原则（第一版用 mock 占位）

---

### 4. `save_log` — 日志保存节点

**职责：**

- 在流程结束前执行
- 在 `logs` 中追加流程结束记录
- 确保 `logs` 和 `errors` 可以完整输出
- 第一版不写外部日志文件

**读取字段：**

| 字段 | 读取目的 |
|------|----------|
| `logs` | 查看已有日志条数，追加完成标记 |
| `errors` | 检查流程中是否有错误（第一版暂不使用） |

**写入字段：**

| 字段 | 写入内容 |
|------|----------|
| `logs` | 追加一条流程完成记录 |

**为什么需要这个节点：**

- 日志节点是流程的"收尾"节点
- 第一版虽然不做外部日志，但保留这个节点位置
- 后续接入真实日志系统时，只需要修改这一个节点

---

## 四、State 字段变化示例

### 输入

```python
session_id = "demo-session-001"
user_message = "我的快递怎么还没到"
image_url = None
image_base64 = None
```

### 初始 State

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

### parse_input 之后

```json
{
  "logs": [
    {
      "node": "parse_input",
      "summary": "收到用户输入：我的快递怎么还没到，图片：无",
      "timestamp": "12:00:00"
    }
  ]
}
```

其他字段不变。

### decide_modality 之后

```json
{
  "modality": "text_only",

  "logs": [
    { "node": "parse_input", "summary": "...", "timestamp": "12:00:00" },
    {
      "node": "decide_modality",
      "summary": "判断为 text_only（有文字、无图片）",
      "timestamp": "12:00:01"
    }
  ]
}
```

### analyze_text 之后

```json
{
  "text_analysis": "用户输入了一段文本，内容是：我的快递怎么还没到",

  "logs": [
    { "node": "parse_input", "summary": "...", "timestamp": "12:00:00" },
    { "node": "decide_modality", "summary": "...", "timestamp": "12:00:01" },
    {
      "node": "analyze_text",
      "summary": "生成文本分析完成",
      "timestamp": "12:00:02"
    }
  ]
}
```

### save_log 之后（最终输出）

```json
{
  "session_id": "demo-session-001",
  "user_message": "我的快递怎么还没到",
  "image_url": null,
  "image_base64": null,

  "modality": "text_only",

  "text_analysis": "用户输入了一段文本，内容是：我的快递怎么还没到",
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

  "logs": [
    {
      "node": "parse_input",
      "summary": "收到用户输入：我的快递怎么还没到，图片：无",
      "timestamp": "12:00:00"
    },
    {
      "node": "decide_modality",
      "summary": "判断为 text_only（有文字、无图片）",
      "timestamp": "12:00:01"
    },
    {
      "node": "analyze_text",
      "summary": "生成文本分析完成",
      "timestamp": "12:00:02"
    },
    {
      "node": "save_log",
      "summary": "流程执行完成，共 4 个节点",
      "timestamp": "12:00:03"
    }
  ],

  "errors": []
}
```

### 变化总结

| 字段 | 初始值 | parse_input | decide_modality | analyze_text | save_log |
|------|--------|-------------|-----------------|--------------|----------|
| `modality` | `"unknown"` | — | `"text_only"` | — | — |
| `text_analysis` | `None` | — | — | `"用户输入了一段文本……"` | — |
| `logs` | `[]` | +1条 | +1条 | +1条 | +1条 |
| `errors` | `[]` | — | — | — | — |

---

## 五、错误处理设计

### Phase 3.1 的错误处理原则

| 原则 | 说明 |
|------|------|
| **不提前复杂化** | 第一版不做 try-except 包裹每个节点 |
| **不静默吞错** | 如果节点异常，LangGraph 会抛出异常，不掩饰 |
| **保留错误位置** | 节点的 `logs` 会记录执行状态，方便定位问题节点 |

### 当前做法

```python
# 节点函数如果正常执行，追加正常日志
# 如果抛出异常，LangGraph 会中断流程并报错
# 不在 Phase 3 做错误恢复
```

### 后续规划

- Phase 5/6 会让 `errors` 参与转人工判断
- 届时节点会捕获异常，把错误信息追加到 `errors`，然后继续流程（走转人工兜底）

---

## 六、为什么暂时不做条件边

### 什么是条件边

LangGraph 的 `add_conditional_edges` 可以根据 State 中的字段值选择不同的下游节点。例如：

```python
graph.add_conditional_edges(
    "analyze_text",
    lambda s: "route_to_skill" if s["intent"] else "save_log",
    {"route_to_skill": "route_to_skill", "save_log": "save_log"},
)
```

### Phase 3.1 不做条件边的理由

| 理由 | 说明 |
|------|------|
| **目标不同** | Phase 3 的目标是验证 LangGraph 基础流转，不是验证路由 |
| **线性流程更简单** | START → A → B → C → END 是对 LangGraph 最基础的测试 |
| **减少干扰** | 如果加了条件边但跑不通，不确定是图配置问题还是节点逻辑问题 |
| **条件边需要 intent** | 条件路由依赖 `intent` 字段，而 Phase 3 还没有实现意图识别 |

### 什么时候加条件边

等到 Phase 4（技能路由阶段）再加入条件边：

```
analyze_text
  ↓ (根据 intent)
route_to_skill → refund_skill / complaint_skill / logistics_skill ...
```

---

## 七、Phase 3.2 实现边界

### 允许修改的文件

| 文件 | 修改内容 |
|------|---------|
| `app/graph.py` | 构建 LangGraph StateGraph，注册 4 个节点，连接线性边 |
| `app/nodes/parse_input.py` | 实现 parse_input 节点函数 |
| `app/nodes/decide_modality.py` | 实现 decide_modality 节点函数 |
| `app/nodes/analyze_text.py` | 实现 analyze_text 节点函数（第一版 mock） |
| `app/nodes/save_log.py` | 实现 save_log 节点函数 |
| `app/main.py` | 修改为调用 graph 构建、创建初始 state、执行流程、输出结果 |
| `tests/test_minimal_graph.py`（新增） | 测试最小图的功能 |

### 不得修改的文件

| 文件 | 为什么不能改 |
|------|-------------|
| `app/skills/*` | Phase 4 才涉及 skill |
| `app/tools/*` | 最小流程不需要外部工具 |
| `app/policies/*` | 最小流程不需要业务规则 |
| `app/memory/*` | 最小流程不需要持久化记忆 |
| `docs/STATE_DESIGN.md` | State 设计已定稿，流程设计不应改变 State |

---

## 八、Phase 3.2 验收标准

### 1. 可运行

```bash
.venv/bin/python -m app.main
```

### 2. 文本输入场景

输入：
```python
"我的快递怎么还没到"
```

输出 JSON 必须包含：

| 字段 | 期望值 |
|------|--------|
| `modality` | `"text_only"` |
| `text_analysis` | 不为 `None`，包含用户输入内容 |
| `logs` | 至少 4 条记录：`parse_input`、`decide_modality`、`analyze_text`、`save_log` |

### 3. 纯图片输入场景

输入：
```python
user_message = ""
image_url = "https://example.com/test.jpg"
```

输出 JSON 必须包含：

| 字段 | 期望值 |
|------|--------|
| `modality` | `"image_only"` |
| `text_analysis` | `None` |
| `logs` | 至少 3 条记录（analyze_text 跳过时也应记录跳过分） |

### 4. 图文输入场景

输入：
```python
user_message = "这个商品怎么样"
image_url = "https://example.com/product.jpg"
```

输出 JSON 必须包含：

| 字段 | 期望值 |
|------|--------|
| `modality` | `"text_with_image"` |
| `text_analysis` | 不为 `None` |
| `logs` | 至少 4 条记录 |

### 5. 测试通过

```bash
.venv/bin/python -m pytest -v
```

### 验收检查清单

| # | 验收项 | 状态 |
|---|--------|------|
| 1 | `.venv/bin/python -m app.main` 可运行 | ⬜ |
| 2 | 文本输入 → `modality` = `"text_only"` | ⬜ |
| 3 | 文本输入 → `text_analysis` 不为空 | ⬜ |
| 4 | 文本输入 → `logs` 至少 4 条 | ⬜ |
| 5 | 纯图片输入 → `modality` = `"image_only"` | ⬜ |
| 6 | 纯图片输入 → `text_analysis` = `None` | ⬜ |
| 7 | 图文输入 → `modality` = `"text_with_image"` | ⬜ |
| 8 | 图文输入 → `text_analysis` 不为空 | ⬜ |
| 9 | `pytest` 全部通过 | ⬜ |

---

## 九、不要过度设计

Phase 3.1 + 3.2 的明确不做什么：

| 不做 | 原因 |
|------|------|
| **不引入真实 LLM** | 第一版用 mock 字符串占位 |
| **不引入真实多模态模型** | `multimodal_analysis` 字段保持 `None` |
| **不引入数据库** | 所有数据在 State 中流转，不需要持久化 |
| **不引入 Dify** | 第一版不接外部 AI 平台 |
| **不引入飞书** | 第一版不需要 IM 集成 |
| **不引入复杂 memory** | 不需要跨会话记忆 |
| **不做 skill 路由** | Phase 4 再做 |
| **不做 policy 决策** | Phase 5 再做 |
| **不做条件边** | Phase 4 再做 |
| **不做错误恢复** | Phase 5/6 再做 |
| **不写外部日志文件** | Phase 6 再说 |

---

> **下一阶段建议**：进入 **Phase 3.2**，根据本文档实现 4 个节点 + 最小 LangGraph 图。
