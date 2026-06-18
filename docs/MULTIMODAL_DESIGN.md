# 多模态路由设计 — MULTIMODAL_DESIGN

> **Phase 7.1 · 设计文档**
> 本文档只做设计讨论，不涉及代码实现。

---

## 一、为什么 Phase 7 要加入多模态路由

### 电商客服中的图片场景

在电商客服中，用户经常发送图片：

- **商品破损** — 用户拍一张实物破损照片，想退货或换货
- **安装问题** — 用户拍摄安装步骤的截图，问怎么装
- **物流截图** — 用户把物流异常的截图发给客服
- **尺码对比** — 用户把尺码表和实物对比拍照，问选哪个尺码
- **商品实物** — 用户拍实物照片，问颜色/款式是否有差异

### 当前流程的问题

Phase 0-6 已完成完整的**文本客服闭环**。但当前流程遇到图片只能做 `text_only` 或 `image_only` 的模态判断，不能有效处理图片。

```
当前流程：
  用户传了图片 → decide_modality 判断为 image_only → 没有分析逻辑
                   ↓
             用户诉求被忽略
```

### Phase 7 的目标

加入多模态路由后：

```
用户传了图片 + 文字 → decide_modality → text_with_image → analyze_multimodal
                                                              ↓
                                                         mock 图文分析
                                                              ↓
                                                        分类节点参考分析结果
```

### 成本控制原则

```
❌ 错误做法：用户一发图片就调用多模态模型
   → 浪费 token、增加延迟

✅ Agent Harness 做法：
   纯图片 → 先追问用户想咨询什么，不调用多模态
   图文混合 → 调用多模态（第一版 mock），在必要时才分析
   先文字后图片 → 从 memory 读取上轮文字，合并分析
```

---

## 二、Phase 7 流程图

### 完整流程

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
                    │decide_modality│← 处理 memory 回溯，写回 combined_text
                    └───────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────────┐
       │text_only │ │image_only│ │text_with_    │
       │          │ │          │ │image         │
       └────┬─────┘ └────┬─────┘ └──────┬───────┘
            │            │              │
            ▼            ▼              ▼
     ┌──────────┐ ┌──────────┐ ┌────────────────┐
     │analyze_  │ │追问回复  │ │analyze_        │
     │text      │ │不调多模态│ │multimodal      │
     └────┬─────┘ └────┬─────┘ └───────┬────────┘
          │            │               │
          └────────────┼───────────────┘
                       ▼
                ┌─────────────────┐
                │ classify_intent  │← 图文场景读取增强文本
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
                │  route_to_skill   │← image_only 由 route_to_skill 写 skill_result
                └────────┬─────────┘
                       ▼
                ┌──────────────────┐
                │ escalation_check  │
                └────────┬─────────┘
                       ▼
                ┌──────────────────┐
                │  generate_reply   │← image_only 在此被检测并固定回复
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

### 新增/修改的路径

| 场景 | 路径 | 变化 |
|------|------|------|
| `text_only` | → `analyze_text` | 不变 |
| `image_only` | → 追问回复（不调多模态） | **新增路径** |
| `text_with_image` | → `analyze_multimodal` | **新增路径** |
| 先文字后图片 | → memory → `analyze_multimodal` | **新增路径** |

---

## 三、modality 路由规则

### 规则总览

```
用户输入
    │
    ├─ 有文字 + 无图片 ──────────→ text_only
    │
    ├─ 无文字 + 有图片 ──────────→ image_only
    │     └─ memory 有上轮文字 ──→ 升级为 text_with_image
    │
    ├─ 有文字 + 有图片 ──────────→ text_with_image
    │
    └─ 无文字 + 无图片 ──────────→ unknown
```

### 1. text_only — 纯文本

| 项目 | 说明 |
|------|------|
| 条件 | `user_message` 不为空，`image_url` / `image_base64` 均为空 |
| 处理 | 走 `analyze_text`（现有流程） |
| 多模态 | 不走 `analyze_multimodal` |

### 2. image_only — 纯图片

| 项目 | 说明 |
|------|------|
| 条件 | `user_message` 为空，`image_url` 或 `image_base64` 不为空 |
| 处理 | **不调用 mock_multimodal_tool**，直接生成追问回复 |
| 多模态 | 不走 `analyze_multimodal` |

**追问回复模板：**

```
我看到您发了一张图片，请问您想咨询这张图片里的什么问题？
比如质量、材质、安装、售后还是价格？
```

**为什么纯图片不直接调用多模态模型：**

```
❌ 用户只发一张图片 → 立刻调多模态
   成本：每次图片都浪费 token
   问题：不知道用户想咨询什么，分析方向不确定

✅ 用户只发一张图片 → 先追问
   成本：零 token
   优势：引导用户补充文字描述，提高后续分析的准确性
```

### 3. text_with_image — 图文混合

| 项目 | 说明 |
|------|------|
| 条件 | `user_message` 不为空，`image_url` 或 `image_base64` 不为空 |
| 处理 | 调用 `mock_multimodal_tool.analyze_mock_image_with_text()` |
| 多模态 | 走 `analyze_multimodal` |
| 写入 | `multimodal_analysis` |

### 4. previous_text + current_image — 先文字后图片

| 项目 | 说明 |
|------|------|
| 条件 | 当前无文字、有图片，且 memory 中存在上轮文字 |
| 处理 | 从 memory 读取上轮文字 + 当前图片 → 升级为 `text_with_image` |
| 多模态 | 走 `analyze_multimodal` |

**实现逻辑（伪代码）：**

```python
if modality == "image_only":
    prev_text = memory.get_last_user_message(session_id)
    if prev_text:
        # 升级为图文分析
        modality = "text_with_image"
        # 关键：把 combined_text 写回 state["user_message"]
        # 这样下游 analyze_multimodal 节点能读取到完整文字
        state["user_message"] = prev_text
    else:
        # 保持纯图片，生成追问
        pass
```

---

## 四、analyze_multimodal 节点设计

### 职责

| 项目 | 说明 |
|------|------|
| 节点名 | `analyze_multimodal` |
| 触发条件 | `modality = "text_with_image"` |
| 处理方式 | 第一版调用 `mock_multimodal_tool`，不接真实多模态模型 |
| 输出 | 写入 `state["multimodal_analysis"]` |

### 读取字段

| 字段 | 读取目的 |
|------|---------|
| `session_id` | 会话标识，用于 memory |
| `user_message` | 用户文本输入 |
| `image_url` | 图片 URL |
| `image_base64` | 图片 base64 编码 |
| `modality` | 确认是 `text_with_image` |

### 写入字段

| 字段 | 写入内容 |
|------|---------|
| `multimodal_analysis` | mock 图文分析结果（dict 或 str） |
| `logs` | 追加一条执行记录 |

### 执行逻辑（伪代码）

```python
def analyze_multimodal(state):
    result = mock_multimodal_tool.analyze_mock_image_with_text(
        user_message=state["user_message"],
        image_url=state["image_url"],
        image_base64=state["image_base64"],
    )

    updated_logs = list(state["logs"])
    updated_logs.append({
        "node": "analyze_multimodal",
        "summary": f"生成多模态分析，confidence={result['confidence']}",
    })

    return {"multimodal_analysis": result, "logs": updated_logs}
```

---

## 五、mock_multimodal_tool 设计

### 函数签名

```python
def analyze_mock_image_with_text(
    user_message: str,
    image_url: str | None = None,
    image_base64: str | None = None,
) -> dict:
    """
    模拟多模态分析。

    第一版不判断真实图片内容，只根据 user_message 生成 mock 分析。
    目的是验证流程完整性，而不是做真实图片识别。

    Args:
        user_message: 用户输入的文本
        image_url: 图片 URL（可选）
        image_base64: 图片 base64（可选）

    Returns:
        dict: 包含 visible_issue、combined_need、confidence 的分析结果
    """
```

### 返回示例

```json
{
  "visible_issue": "疑似商品破损或用户关注图片细节",
  "combined_need": "结合文字判断，用户可能在咨询售后/质量/退款问题",
  "confidence": 0.75
}
```

### 返回字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `visible_issue` | `str` | 图片中可见的问题描述（mock） |
| `combined_need` | `str` | 结合文字后的综合需求判断（mock） |
| `confidence` | `float` | 分析置信度 |

### 设计原则

```
Tool 只负责提供外部数据，不负责业务决策。
```

- `mock_multimodal_tool` 是 **Tool**，不是 **Skill**
- 不判断真实图片内容
- 只用于验证流程完整性
- 后续可以替换为真实多模态模型

> ⚠️ **`combined_need` 字段说明：** 本字段是 mock 占位数据，设计上略微靠近业务判断边界。
> 在真实实现中，`combined_need` 应由 LLM 或分类节点生成，Tool 只输出原始观测（`visible_issue`）。
> Phase 7 mock 版本保留此字段仅用于验证流程，不作为最终架构参考。

---

## 六、conversation_memory 设计

### 为什么需要 memory

用户可能先发文字后发图片：

```
用户：这个怎么安装（第一轮）
用户：[图片]（第二轮，只有图片）
```

如果不保存上轮文字，第二轮无法理解用户想咨询安装问题。

### 设计

第一版使用**简单内存 dict**，不接数据库、不接 Redis。

```python
class ConversationMemory:
    """简易会话记忆，保存每个 session 最近一轮 user_message。"""

    def __init__(self):
        self._store: dict[str, str] = {}

    def save_last_user_message(self, session_id: str, user_message: str) -> None:
        """保存最近一轮 user_message。"""
        if user_message:
            self._store[session_id] = user_message

    def get_last_user_message(self, session_id: str) -> str | None:
        """读取最近一轮 user_message。"""
        return self._store.get(session_id)
```

### 使用位置

| 位置 | 做什么 |
|------|--------|
| `parse_input` 或 `decide_modality` | 当检测到 `image_only` 时，调用 `get_last_user_message()` |
| `parse_input` | 每次收到用户文字时，调用 `save_last_user_message()` |

### 边界说明

| 不做什么 | 原因 |
|---------|------|
| 不做复杂多轮记忆 | 只保存最近一轮，不需要完整对话树 |
| 不做持久化 | 内存 dict，关闭程序后丢失 |
| 不接 Redis / PostgreSQL | 第一版不需要 |
| 不保存图片 | 图片在 State 中流转，不在 memory 中重复存储 |

---

## 七、generate_reply 对 image_only 的处理

### 规则

当 `modality = "image_only"` 且没有上轮文字可回溯时：

```python
if modality == "image_only":
    reply = "我看到您发了一张图片，请问您想咨询这张图片里的什么问题？比如质量、材质、安装、售后还是价格？"
```

### 对应的 State 字段

| 字段 | 值 | 写入者 |
|------|-----|--------|
| `modality` | `"image_only"` | `decide_modality` |
| `multimodal_analysis` | `None` | — |
| `selected_skill` | `None` | `route_to_skill`（直接设置） |
| `skill_result` | `{"action": "image_clarification"}` | `route_to_skill`（直接设置，不经过 skill 节点） |
| `need_human` | `False` | `escalation_check` |
| `reply` | 追问文本 | `generate_reply` |

### image_only 走完整管线的说明

`image_only` 仍然经过完整的分类 → 路由 → 转人工 → 回复生成管线，而不是提前跳出。原因：

1. **保持图结构统一** — 所有输入走相同节点序列，减少特殊分支
2. **为后续扩展保留** — 如果后续 image_only 也需要分析，流程已经就绪
3. **实际覆盖发生在最后** — `generate_reply` 检测到 `modality == "image_only"` 且 `skill_result["action"] == "image_clarification"` 时，覆盖为固定追问模板

```
route_to_skill: 检测到 image_only → selected_skill=None, skill_result={"action": "image_clarification"}
...
generate_reply: 检测到 image_only → 覆盖 reply 为固定追问模板
```

### 为什么不调多模态

```
用户只发一张破损照片 →
  无文字说明
  不知道用户想退货、抱怨还是问怎么修复
  调用多模态也猜不准用户意图

→ 先追问，让用户补充文字
→ 下一轮有文字+图片时再调多模态
→ 节省 token，提高分析准确率
```

---

## 八、分类节点如何使用 multimodal_analysis

### 当前的问题

Phase 4 的分类节点只基于 `user_message` 做关键词匹配。当用户发图文时，`user_message` 可能很短（如"这个"），关键词匹配不准确。

### Phase 7 的改进

当 `multimodal_analysis` 不为空时，分类节点应结合 `user_message` 和 `multimodal_analysis`：

```python
def classify_intent(state):
    text = state["user_message"]

    # 如果有 multimodal_analysis，拼接分析结果以增强分类
    multimodal = state.get("multimodal_analysis")
    if multimodal:
        combined = text + " " + multimodal.get("combined_need", "")
    else:
        combined = text

    # 用 combined_text 做关键词匹配
    # ...
```

### 处理流程

```
用户输入： "这个破了" + 破损图片
                    ↓
mock_multimodal_tool 返回：
  combined_need = "用户可能在咨询售后/质量/退款问题"
                    ↓
classify_intent 读取 combined_text：
  "这个破了 用户可能在咨询售后/质量/退款问题"
                    ↓
  关键词"退款"命中 → intent = "refund_request"
```

### 注意

- 第一版只是简单拼接文本，不使用真实 LLM
- `multimodal_analysis` 用于**增强**关键词匹配，而不是替代
- 纯文本场景不受影响

> ⚠️ **设计变更说明：** Phase 7 打破了 Phase 4 分类节点"只依赖 `user_message`"的单输入原则。
> 原因：图文场景下 `user_message` 可能很短（如"这个"），单独依赖它无法准确匹配关键词。
> 拼接 `multimodal_analysis` 后，关键词匹配可以命中"退款"、"投诉"等核心词。
> 这个变更**只影响图文场景**，纯文本路径不受影响。

---

## 九、示例输入输出

### 示例 1：纯图片 — 追问

**输入：**
- `image_url = "https://example.com/broken.jpg"`
- `user_message = ""`

**输出：**
```json
{
  "modality": "image_only",
  "multimodal_analysis": null,
  "selected_skill": null,
  "skill_result": {
    "action": "image_clarification"
  },
  "need_human": false,
  "reply": "我看到您发了一张图片，请问您想咨询这张图片里的什么问题？比如质量、材质、安装、售后还是价格？"
}
```

### 示例 2：图片 + 文字 — 退款售后

**输入：**
- `user_message = "这个破了能退吗"`
- `image_url = "https://example.com/broken.jpg"`

**输出：**
```json
{
  "modality": "text_with_image",
  "multimodal_analysis": {
    "visible_issue": "疑似商品破损或用户关注图片细节",
    "combined_need": "结合文字判断，用户可能在咨询售后/质量/退款问题",
    "confidence": 0.75
  },
  "intent": "refund_request",
  "selected_skill": "refund_skill",
  "skill_result": {
    "action": "retention",
    "message": "首次退款，先进入挽留流程"
  },
  "reply": "非常抱歉让您有不好的体验，我先帮您看一下这个问题。……"
}
```

### 示例 3：先文字后图片 — 安装问题

**第一轮输入：**
- `user_message = "这个怎么安装"`

**第二轮输入：**
- `image_url = "https://example.com/install.jpg"`
- `user_message = ""`

**记忆：**
- `memory.get_last_user_message("session-001")` → `"这个怎么安装"`

**第二轮输出：**
```json
{
  "modality": "text_with_image",
  "multimodal_analysis": {
    "visible_issue": "用户可能展示了安装位置的图片",
    "combined_need": "结合上轮文字判断，用户可能咨询商品安装/使用方法",
    "confidence": 0.70
  },
  "intent": "product_question",
  "selected_skill": "product_qa_skill",
  "reply": "您咨询的商品信息如下：……"
}
```

### 示例 4：普通纯文本 — 物流查询（不受影响）

**输入：**
- `user_message = "我的快递怎么还没到"`

**输出：**
```json
{
  "modality": "text_only",
  "multimodal_analysis": null,
  "intent": "logistics_question",
  "selected_skill": "logistics_skill",
  "reply": "感谢您的耐心等待，我来帮您查看一下物流信息。……"
}
```

---

## 十、Phase 7.2 实现边界

### 允许修改的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/nodes/decide_modality.py` | **更新** | 增加 image_only 的追问逻辑 + memory 回溯 |
| `app/nodes/analyze_multimodal.py` | **新建** | 多模态分析节点 |
| `app/nodes/classify_intent.py` | **更新** | 读取 `multimodal_analysis` 增强匹配 |
| `app/nodes/classify_emotion.py` | **更新** | 同上 |
| `app/nodes/classify_stage.py` | **更新** | 同上 |
| `app/nodes/route_to_skill.py` | **更新** | 处理 `image_clarification` 路由 |
| `app/nodes/generate_reply.py` | **更新** | 增加 `image_only` 的追问模板 |
| `app/tools/mock_multimodal_tool.py` | **新建** | mock 多模态分析工具 |
| `app/memory/conversation_memory.py` | **新建** | 简易内存会话记忆 |
| `app/graph.py` | **更新** | 注册 `analyze_multimodal` 节点 |
| `app/main.py` | **更新** | 展示图片相关 demo |
| `tests/test_multimodal_routing.py` | **新建** | 测试多模态路由 |

### 不得修改的文件

| 文件 | 原因 |
|------|------|
| `docs/STATE_DESIGN.md` | State 设计已定稿 |
| `docs/GRAPH_DESIGN.md` | 图基础结构已定稿 |
| `docs/CLASSIFICATION_DESIGN.md` | 分类设计已定稿 |
| `docs/SKILL_POLICY_DESIGN.md` | Skill/Policy 设计已定稿 |
| `docs/REPLY_DESIGN.md` | 回复设计已定稿 |
| `app/state/customer_state.py` | State 定义已定稿 |
| `app/policies/*` | Policy 逻辑已定稿 |

---

## 十一、Phase 7.2 验收标准

| # | 验收项 | 验证方式 |
|---|--------|---------|
| 1 | `.venv/bin/python -m app.main` 可运行 | 直接运行 |
| 2 | `.venv/bin/python -m pytest` 全部通过 | 运行测试 |
| 3 | **纯图片** → `modality` = `"image_only"` | 断言检查 |
| 4 | **纯图片** → `multimodal_analysis` is `None` | 断言检查 |
| 5 | **纯图片** → `selected_skill` is `None` | 断言检查 |
| 6 | **纯图片** → `skill_result["action"]` = `"image_clarification"` | 断言检查 |
| 7 | **纯图片** → `reply` 包含追问文本 | 断言检查 |
| 8 | **纯图片** → 不调用 `mock_multimodal_tool` | 断言检查 |
| 9 | **图文混合** → `modality` = `"text_with_image"` | 断言检查 |
| 10 | **图文混合** → `multimodal_analysis` 不为空 | 断言检查 |
| 11 | **先文字后图片** → memory 读取成功，升级为 `text_with_image` | 断言检查 |
| 12 | **纯文本** → 现有流程不受影响（如物流查询） | 断言检查 |
| 13 | 没有接真实多模态模型 | 代码审查 |
| 14 | 没有接数据库 | 代码审查 |

---

## 十二、不要过度设计

Phase 7 明确不做的事：

| 不做 | 原因 |
|------|------|
| **不接真实多模态模型** | 第一版用 mock，验证流程完整性 |
| **不做真实 OCR** | 不需要识别图片中的文字 |
| **不做真实图片识别** | 不需要判断图片内容 |
| **不做复杂多轮记忆** | 只保存最近一轮 user_message |
| **不接 Redis / PostgreSQL** | 内存 dict 就够用 |
| **不接飞书图片消息** | 第一版不需要 IM 集成 |
| **不接真实电商平台图片** | mock 数据已够验证流程 |
| **不持久化 memory** | 关闭后丢失可以接受 |
| **不保存图片到 memory** | 图片在 State 中流转 |
| **不把图片分析结果当真实结论** | 明确标注为 mock 数据 |

---

> **下一阶段建议**：进入 **Phase 7.2**，根据本文档实现多模态路由。
