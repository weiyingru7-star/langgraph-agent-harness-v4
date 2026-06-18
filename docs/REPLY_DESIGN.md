# 回复生成设计 — REPLY_DESIGN

> **Phase 6.1 · 设计文档**
> 本文档只做设计讨论，不涉及代码实现。

---

## 一、为什么 Phase 6 要加入 generate_reply

### 当前阶段的问题

到 Phase 5 为止，Agent 已经能完成以下动作：

```
用户输入 → 理解意图 → 选择技能 → 执行 mock 业务逻辑 → 判断转人工
                               ↓
                         skill_result = 结构化数据
                               ↓
                         但用户看不到这个数据
```

Phase 5 的输出示例：

```json
{
  "intent": "refund_request",
  "selected_skill": "refund_skill",
  "policy_decision": "retention",
  "skill_result": {
    "action": "retention",
    "message": "首次退款，先进入挽留流程"
  },
  "reply": null   ← 还没有生成回复
}
```

`skill_result` 是结构化数据，适合程序读取，但不适合直接展示给用户。

| 对比 | 结构化数据（skill_result） | 自然语言回复（reply） |
|------|--------------------------|---------------------|
| **示例** | `{"order_id": "ORD-001", "status": "已发货", "eta": "预计明天到达"}` | "您的快递已发货，单号 SF1234567890，预计明天到达" |
| **谁读** | 程序/下一个节点 | 用户 |
| **格式** | JSON dict | 自然语言文本 |
| **特点** | 精确、结构化、适合逻辑处理 | 友好、完整、适合直接展示 |

### Phase 6 要解决的问题

`generate_reply` 负责把结构化结果**翻译成自然语言回复**：

```
skill_result = {"action": "retention", ...}
                    ↓
reply = "非常抱歉让您有不好的体验……目前系统判断这是首次退款请求……"
```

### 为什么 Phase 6 才做回复生成

| 阶段 | 完成的内容 | 能否生成回复 |
|------|-----------|------------|
| Phase 2-3 | State 定义 + 最小图流转 | ❌ 没有分类结果 |
| Phase 4 | 意图/情绪/阶段分类 | ❌ 没有 skill_result |
| Phase 5 | 技能执行 + 策略决策 | ✅ 所有输入就绪 |
| **Phase 6** | **回复生成** | **现在可以做** |

---

## 二、Phase 6 流程图

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
                           ▼
                    ┌──────────────┐
                    │ analyze_text │
                    └───────┬──────┘
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
                    │  generate_reply   │  ← 新增
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

### 新增节点位置

`generate_reply` 放在 `escalation_check` 之后、`save_log` 之前。原因是：

1. 此时 `skill_result`、`policy_decision`、`need_human` 都已就绪
2. `generate_reply` 需要读取所有这些字段来生成回复
3. `save_log` 作为最后一个节点，保存包含 `reply` 的完整 state

---

## 三、generate_reply 节点职责

### 读取字段

| 字段 | 读取目的 |
|------|---------|
| `intent` | 用户想做什么，决定回复主题 |
| `emotion` | 用户情绪，决定共情语气 |
| `emotion_score` | 情绪强度，决定共情程度 |
| `customer_stage` | 客户阶段，帮助定位上下文 |
| `selected_skill` | 调用了哪个 skill，决定回复模板 |
| `skill_result` | skill 执行结果，回复的核心数据 |
| `policy_decision` | 策略决策结果，影响回复方向 |
| `need_human` | 是否转人工，优先级最高 |
| `human_reason` | 转人工的原因 |
| `errors` | 系统错误信息 |

### 写入字段

| 字段 | 说明 |
|------|------|
| `reply` | 生成的客服回复文本 |
| `logs` | 追加一条执行记录 |

---

## 四、回复结构

所有客服回复遵循**四段结构**：

```
┌─────────────────────────────────────────┐
│  1. 共情                                │
│  "非常抱歉让您有不好的体验"              │
│  "我理解您现在比较着急"                  │
│  "感谢您的耐心等待"                      │
├─────────────────────────────────────────┤
│  2. 事实说明                             │
│  "您的快递已发货，单号 SF1234567890"     │
│  "目前系统判断这是首次退款请求"          │
│  "您咨询的商品信息如下："                │
├─────────────────────────────────────────┤
│  3. 解决方案                             │
│  "预计明天到达"                          │
│  "我们会优先帮您确认问题原因"            │
│  "已进入换货流程"                        │
├─────────────────────────────────────────┤
│  4. 下一步动作                           │
│  "如有其他问题欢迎继续咨询"              │
│  "正在为您转接人工客服"                  │
│  "您可以先把具体问题发我"                │
└─────────────────────────────────────────┘
```

### 完整示例

**用户说：** "质量太差了我要退款"

```
非常抱歉让您有不好的体验，我先帮您看一下这个问题。         ← 共情
目前系统判断这是首次退款请求，                          ← 事实说明
我们会优先帮您确认问题原因，并尝试给出补偿或处理方案。     ← 解决方案
您可以先把具体质量问题发我，如果您仍然坚持退款，
我们会继续为您处理。                                   ← 下一步动作
```

**用户说：** "我的快递怎么还没到"

```
感谢您的耐心等待，我来帮您查看一下物流信息。             ← 共情
您的快递已发货，单号 SF1234567890，                     ← 事实说明
目前状态是"已发货"，预计明天到达。                       ← 解决方案
请您耐心等待，如有其他问题随时联系我们。                 ← 下一步动作
```

---

## 五、不同场景回复规则

### 1. logistics_skill — 物流查询

**触发条件：** `selected_skill = "logistics_skill"`

**伪代码：**

```python
order = skill_result.get("order_info", {})
reply = (
    f"感谢您的耐心等待，我来帮您查看一下物流信息。\n"
    f"您的快递已发货，单号 {order.get('tracking_no', '—')}，\n"
    f"目前状态是"{order.get('status', '—')}"，预计 {order.get('eta', '—')}。\n"
    f"请您耐心等待，如有其他问题随时联系我们。"
)
```

**模板：**
- 共情 → "感谢您的耐心等待"
- 事实 → 物流单号、状态
- 解决 → 预计到达时间
- 下一步 → 如有问题再联系

---

### 2. refund_skill + retention — 首次退款挽留

**触发条件：** `selected_skill = "refund_skill"` 且 `policy_decision = "retention"`

**伪代码：**

```python
# policy_decision 由 refund_policy 根据 refund_count 决定
# Phase 5 中 refund_count mock 为 1，对应 retention
decision = policy_decision  # "retention" / "refund_workflow" / "direct_refund_or_human_confirm"

if decision == "retention":
    reply = (
        f"非常抱歉让您有不好的体验，我先帮您看一下这个问题。\n"
        f"目前系统判断这是首次退款请求，我们会优先帮您确认问题原因，"
        f"并尝试给出补偿或处理方案。\n"
        f"您可以先把具体质量问题发我，我会继续帮您判断是换货、补偿"
        f"还是进入退款流程。\n"
        f"如果您仍然坚持退款，我们会继续为您处理。"
    )
elif decision == "refund_workflow":
    reply = (
        f"好的，已为您记录第二次退款请求。\n"
        f"系统已启动退款流程，我们的工作人员会尽快处理。\n"
        f"退款金额将原路返回，预计 3-5 个工作日到账。\n"
        f"如有其他问题欢迎随时联系我们。"
    )
else:
    reply = (
        f"已记录您的退款请求。\n"
        f"由于多次退款请求，此问题需要人工确认处理。\n"
        f"正在为您转接人工客服，他们会进一步核实并处理。\n"
        f"请稍候。"
    )
```

**注意：**
- 一定要先共情
- 不能直接说"已经为您退款"
- 说明首次退款→先确认问题→多种方案可选
- 给用户自主选择权

---

### 3. product_qa_skill — 商品问答

**触发条件：** `selected_skill = "product_qa_skill"`

**伪代码：**

```python
product = skill_result.get("product_info", {})
reply = (
    f"您咨询的商品信息如下：\n"
    f"商品名称：{product.get('product_name', '—')}\n"
    f"材质：{product.get('material', '—')}\n"
    f"尺码：{product.get('size', '—')}\n"
    f"特点：{'、'.join(product.get('features', []))}\n"
    f"适用场景：{product.get('suitable_scene', '—')}\n"
    f"如果您需要了解更多信息，欢迎继续咨询。"
)
```

---

### 4. recommendation_skill — 商品推荐

**触发条件：** `selected_skill = "recommendation_skill"`

**伪代码：**

```python
product = skill_result.get("product_info", {})
reply = (
    f"根据您的需求，我为您推荐以下商品：\n"
    f"{product.get('product_name', '—')}\n"
    f"特点：{'、'.join(product.get('features', []))}\n"
    f"适用场景：{product.get('suitable_scene', '—')}\n"
    f"如果您对这款商品感兴趣，可以告诉我，我可以提供更多详情。"
)
```

---

### 5. exchange_skill — 换货处理

**触发条件：** `selected_skill = "exchange_skill"`

**伪代码：**

```python
reply = (
    f"好的，我来帮您处理换货。\n"
    f"已进入换货流程，下一步需要您确认以下信息：\n"
    f"1. 订单号\n"
    f"2. 您想要更换的尺码/颜色\n"
    f"3. 收货地址是否变更\n"
    f"请提供相关信息，我会继续为您处理。"
)
```

---

### 6. complaint_skill — 投诉处理

**触发条件：** `selected_skill = "complaint_skill"`

**伪代码：**

```python
reply = (
    f"非常抱歉给您带来这么不好的体验，我理解您现在的心情。\n"
    f"已经记录您的投诉信息，我们会高度重视。\n"
    f"由于投诉需要专人处理，我将为您转接人工客服，"
    f"他们会进一步跟进您的问题。\n"
    f"请您耐心等待，感谢您的反馈。"
)
```

---

### 7. human_skill — 转人工

**触发条件：** `selected_skill = "human_skill"` 或 `need_human = True`

**伪代码：**

```python
reply = (
    f"我理解您现在需要人工帮助。\n"
    f"{'问题说明：' + human_reason + '\n' if human_reason else ''}"
    f"正在为您转接人工客服，请稍候。\n"
    f"我会把当前问题和已识别的信息一起交给人工客服，"
    f"方便他们快速为您处理。"
)
```

**注意：**
- `need_human = True` 时，转人工提示优先级最高
- 但仍然保留简短的业务上下文（通过 `human_reason`）
- 不要继续让用户提供详细信息（交给人工客服）

---

### 8. smalltalk_fallback — 闲聊兜底

**触发条件：** `skill_result["action"] == "smalltalk_fallback"`

**伪代码：**

```python
reply = "您好，我在的。请问有什么可以帮您？"
```

**规则：**
- 最简单、最简短的回复
- 不转人工
- 不调用业务 skill
- 语气友好、开放

---

## 六、need_human 优先级

### 核心规则

```
如果 need_human = True → 回复中必须包含转人工提示
如果 need_human = False → 正常生成业务回复
```

### 为什么转人工优先级最高

如果用户已经情绪失控或明确要求人工，再继续自动回复会让用户更生气。此时应该：

1. **先共情** — 承认用户的情绪
2. **说明转人工** — 明确告诉用户正在转接
3. **保留上下文** — 已识别的信息可以交给人工客服

### 转人工回复的结构

```
┌─────────────────────────────────────────┐
│  1. 共情                                │
│  "我理解您现在比较着急"                  │
├─────────────────────────────────────────┤
│  2. 事实说明（可选）                     │
│  "已记录您的问题信息"                    │
├─────────────────────────────────────────┤
│  3. 解决方案（转人工）                   │
│  "正在为您转接人工客服"                  │
├─────────────────────────────────────────┤
│  4. 下一步                               │
│  "请稍候，信息已同步给人工客服"          │
└─────────────────────────────────────────┘
```

### 优先级判断逻辑（伪代码）

```python
def generate_reply(state):
    if state["need_human"]:
        return _human_transfer_reply(state)

    skill = state["selected_skill"]
    if skill == "logistics_skill":
        return _logistics_reply(state)
    elif skill == "refund_skill":
        return _refund_reply(state)
    elif skill == "product_qa_skill":
        return _product_qa_reply(state)
    # ... 其他 skill ...
    else:
        return _fallback_reply(state)
```

---

## 七、第一版为什么不用真实 LLM

### 模板方案 vs LLM 方案

| 维度 | 模板方案（Phase 6 第一版） | LLM 方案（后续升级） |
|------|--------------------------|-------------------|
| 实现复杂度 | 低——if-else + f-string | 高——需要接入 LLM、处理 token |
| 可控性 | 高——每句话都可预期 | 低——LLM 可能自由发挥 |
| 测试稳定性 | 高——输入确定输出确定 | 低——相同输入可能不同输出 |
| 维护成本 | 低——改模板即可 | 高——需要调 prompt、处理边界 |
| 回复自然度 | 中——模板化但可用 | 高——接近真人客服 |

### 为什么第一版选模板

1. **验证流程完整性** — Phase 6 的核心目标是验证 `reply` 字段能被正确写入，回复质量可以后续迭代
2. **可控** — 模板回复不会出现"帮您退款了"这种错误
3. **可测试** — 断言 `reply` 包含特定关键词，而不是模糊匹配
4. **不绕过 Policy** — LLM 如果直接生成回复可能忽略 `policy_decision`，模板永远不会

### 后续升级路径

```python
# Phase 6（模板版本）：
def generate_reply(state):
    return {"reply": _template_reply(state), "logs": logs}

# 后续（LLM 版本）：
def generate_reply(state):
    prompt = _build_reply_prompt(state)  # 用 State 字段构建 prompt
    reply = llm_call(prompt)
    return {"reply": reply, "logs": logs}

# 升级时只需要修改 generate_reply 内部逻辑
# 调用方（Graph、测试）完全不受影响
```

---

## 八、示例输入输出

### 示例 1：物流查询

**输入：**
- `user_message = "我的快递怎么还没到"`
- `selected_skill = "logistics_skill"`
- `skill_result = {"order_info": {"tracking_no": "SF1234567890", "status": "已发货", "eta": "预计明天到达"}}`
- `need_human = False`

**输出 reply：**

```
感谢您的耐心等待，我来帮您查看一下物流信息。
您的快递已发货，单号 SF1234567890，
目前状态是"已发货"，预计明天到达。
请您耐心等待，如有其他问题随时联系我们。
```

---

### 示例 2：首次退款挽留

**输入：**
- `user_message = "质量太差了我要退款"`
- `selected_skill = "refund_skill"`
- `policy_decision = "retention"`
- `need_human = True`（emotion_score=0.9 > 0.85）
- `human_reason = "用户情绪评分过高"`

**输出 reply：**

```
非常抱歉让您有不好的体验，我理解您现在的心情。
问题说明：用户情绪评分过高
目前系统判断这是首次退款请求。
由于当前情况，这个问题会由人工客服为您处理，会更高效一些。
正在为您转接人工客服，请稍候。我会把当前问题和已识别的信息
一起交给人工客服，方便他们快速为您处理。
```

> 注意：由于 `need_human = True`，即使业务是退款挽留，回复也优先转人工。
> 这是预期行为——情绪激动时自动回复可能火上浇油。

---

### 示例 3：商品咨询

**输入：**
- `user_message = "这个衣服是什么材质"`
- `selected_skill = "product_qa_skill"`
- `skill_result = {"product_info": {"product_name": "经典款运动鞋", "material": "透气网面 + EVA 鞋底", "size": "39-44码可选", "features": ["轻便", "防滑", "透气"], "suitable_scene": "日常跑步、健身、休闲穿着"}}`
- `need_human = False`

**输出 reply：**

```
您咨询的商品信息如下：
商品名称：经典款运动鞋
材质：透气网面 + EVA 鞋底
尺码：39-44码可选
特点：轻便、防滑、透气
适用场景：日常跑步、健身、休闲穿着
如果您需要了解更多信息，欢迎继续咨询。
```

---

### 示例 4：转人工

**输入：**
- `user_message = "气死了，我要人工"`
- `selected_skill = "human_skill"`
- `need_human = True`
- `human_reason = "用户情绪评分过高；用户要求转人工"`

**输出 reply：**

```
我理解您现在需要人工帮助。
问题说明：用户情绪评分过高；用户要求转人工
正在为您转接人工客服，请稍候。
我会把当前问题和已识别的信息一起交给人工客服，方便他们快速为您处理。
```

---

### 示例 5：投诉

**输入：**
- `user_message = "你们这个太垃圾了，我要投诉"`
- `selected_skill = "complaint_skill"`
- `need_human = True`
- `human_reason = "用户情绪评分过高；投诉需要人工处理"`

**输出 reply：**

```
非常抱歉给您带来这么不好的体验，我理解您现在的心情。
已经记录您的投诉信息，我们会高度重视。
由于投诉需要专人处理，我将为您转接人工客服，他们会进一步跟进您的问题。
请您耐心等待，感谢您的反馈。
```

---

### 示例 6：换货

**输入：**
- `user_message = "我要换个尺码"`
- `selected_skill = "exchange_skill"`
- `need_human = False`

**输出 reply：**

```
好的，我来帮您处理换货。
已进入换货流程，下一步需要您确认以下信息：
1. 订单号
2. 您想要更换的尺码/颜色
3. 收货地址是否变更
请提供相关信息，我会继续为您处理。
```

---

### 示例 7：闲聊

**输入：**
- `user_message = "你好，在吗"`
- `selected_skill = None`
- `skill_result = {"action": "smalltalk_fallback"}`
- `need_human = False`

**输出 reply：**

```
您好，我在的。请问有什么可以帮您？
```

---

## 九、Phase 6.2 实现边界

### 允许修改的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/nodes/generate_reply.py` | **新建** | 模板回复生成 |
| `app/graph.py` | **更新** | 在 escalation_check 之后注册 generate_reply |
| `app/main.py` | **更新** | 展示 reply 字段 |
| `app/tests/test_generate_reply.py` | **新建** | 测试 7 个场景的回复 |

### 不得修改的文件

| 文件 | 原因 |
|------|------|
| `docs/STATE_DESIGN.md` | State 设计已定稿 |
| `docs/GRAPH_DESIGN.md` | 图基础结构已定稿 |
| `docs/CLASSIFICATION_DESIGN.md` | 分类设计已定稿 |
| `docs/SKILL_POLICY_DESIGN.md` | Skill/Policy 设计已定稿 |
| `app/state/customer_state.py` | State 定义已定稿 |
| `app/skills/*` | Skill 逻辑已定稿 |
| `app/tools/*` | Tool 逻辑已定稿 |
| `app/policies/*` | Policy 逻辑已定稿 |

---

## 十、Phase 6.2 验收标准

| # | 验收项 | 验证方式 |
|---|--------|---------|
| 1 | `.venv/bin/python -m app.main` 可运行 | 直接运行 |
| 2 | `.venv/bin/python -m pytest` 全部通过 | 运行测试 |
| 3 | 每个 demo 的 `reply` 不为空 | 断言检查 |
| 4 | 物流查询 → `reply` 包含物流信息 | 断言检查 |
| 5 | 退款挽留 → `reply` 包含共情和挽留说明 | 断言检查 |
| 6 | 商品咨询 → `reply` 包含商品信息 | 断言检查 |
| 7 | 转人工 → `reply` 包含转人工说明 | 断言检查 |
| 8 | 闲聊 → `reply` 为兜底回复 | 断言检查 |
| 9 | 没有接真实 LLM | 代码审查 |
| 10 | 没有让 LLM 直接做退款决策 | 代码审查 |

---

## 十一、不要过度设计

Phase 6 明确不做的事：

| 不做 | 原因 |
|------|------|
| **不接真实 LLM** | 第一版用模板，可控可测试 |
| **不接 Dify** | 第一版不依赖外部 AI 平台 |
| **不接数据库** | 回复数据在 State 中即可 |
| **不接飞书** | 第一版不需要 IM 集成 |
| **不接真实订单 API** | mock 数据已够验证流程 |
| **不做复杂多轮记忆** | 每个回复独立生成 |
| **不做多模态真实识别** | 第一版不涉及图片理解 |
| **不做多语言** | 第一版只支持中文 |
| **不做实时翻译** | 不需要 |
| **不做情感计算升级** | 第一版基于规则即可 |

---

> **下一阶段建议**：进入 **Phase 6.2**，根据本文档实现 `generate_reply` 节点。
