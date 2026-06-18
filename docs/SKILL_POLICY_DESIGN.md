# Skill / Tool / Policy 设计 — SKILL_POLICY_DESIGN

> **Phase 5.1 · 设计文档**
> 本文档只做设计讨论，不涉及代码实现。

---

## 一、为什么 Phase 5 要加入 Skill / Tool / Policy

### 当前进展回顾

截至 Phase 4，项目完成了以下能力：

```
用户输入 → 解析 → 模态判断 → 文本分析 → 意图分类 → 情绪分类 → 阶段分类 → 日志 → 结束
                                          ↑
                                     LLM 负责"理解"
```

问题是：**理解了用户想做什么，然后呢？**

- `intent = "refund_request"` → 但没有人处理退款
- `intent = "logistics_question"` → 但没有人查询物流
- `emotion_score = 0.9` → 但没有人判断是否需要转人工

Phase 5 的目标是：让 Agent 从"理解用户"进入"执行客服动作"。

### Phase 5 增加的三层

| 层次 | 职责 | 示例 |
|------|------|------|
| **Skill** | 封装客服业务能力 | 退款处理、商品问答、物流查询 |
| **Tool** | 访问外部系统（第一版用 mock） | 查订单、查商品 |
| **Policy** | 确定性业务规则 | 退款规则、转人工规则 |

### 这些层次为什么不能交给 LLM

```
❌ 错误做法：
  Prompt 里写 "如果用户第一次退款先挽留"
  → LLM 可能忽略规则、被 prompt injection 绕过

✅ Agent Harness 做法：
  LLM 输出 intent = "refund_request"
  refund_policy.py 根据退款次数做决策
  State 保存 policy_decision = "retention"
```

这体现了 Agent Harness 的核心边界：

> **LLM 负责"理解"，Skill 负责"封装业务能力"，Tool 负责"访问外部系统"，Policy 负责"确定性决策"。**

---

## 二、Phase 5 流程图

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
                    │  route_to_skill   │  ← 新增
                    └────────┬─────────┘
                           ▼
                    ┌──────────────────┐
                    │ escalation_check  │  ← 新增
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

### 新增节点说明

| 节点 | 职责 | 在流程中的位置 |
|------|------|--------------|
| `route_to_skill` | 根据 intent 选择 skill，执行 mock 业务逻辑 | classify_stage 之后，escalation_check 之前 |
| `escalation_check` | 检查是否需要转人工，由 policy 决定 | route_to_skill 之后，save_log 之前 |

### 为什么 Phase 5 还没有 generate_reply

`generate_reply` 负责把 `skill_result` 和 `policy_decision` 翻译成自然语言回复。Phase 5 先关注 **技能执行和规则判断是否正确**，回复生成留到 Phase 6。Phase 5 执行后可以通过 `skill_result` 和 `policy_decision` 验证结果。

---

## 三、Skill 设计

Skill 是客服业务能力的载体。每个 Skill 只做自己负责的一件事。

### 1. product_qa_skill — 商品问答

| 项目 | 说明 |
|------|------|
| 触发条件 | `intent = "product_question"` |
| 职责 | 回答商品材质、尺寸、参数、使用方法等问题 |
| 调用工具 | `mock_product_tool` |
| 读取字段 | `user_message`, `intent` |
| 写入字段 | `skill_result` |

**执行逻辑（伪代码）：**

```python
def product_qa_skill(state):
    # 调用 mock 工具获取商品信息
    product = mock_product_tool.get_mock_product_info()

    return {
        "skill_result": {
            "action": "product_answer",
            "product_info": {
                "product_name": product["product_name"],
                "material": product["material"],
                "size": product["size"],
                "features": product["features"],
                "suitable_scene": product["suitable_scene"],
            },
            "message": "已查询商品基础信息",
        }
    }
```

### 2. recommendation_skill — 商品推荐

| 项目 | 说明 |
|------|------|
| 触发条件 | `intent = "recommendation"` |
| 职责 | 根据用户需求做售前推荐 |
| 调用工具 | `mock_product_tool` |
| 读取字段 | `user_message`, `intent` |
| 写入字段 | `skill_result` |

**执行逻辑（伪代码）：**

```python
def recommendation_skill(state):
    product = mock_product_tool.get_mock_product_info()
    return {
        "skill_result": {
            "action": "recommendation",
            "product_info": {
                "product_name": product["product_name"],
                "material": product["material"],
                "size": product["size"],
                "features": product["features"],
                "suitable_scene": product["suitable_scene"],
            },
            "message": "已根据用户需求生成推荐信息",
        }
    }
```

### 3. logistics_skill — 物流查询

| 项目 | 说明 |
|------|------|
| 触发条件 | `intent = "logistics_question"` |
| 职责 | 查询 mock 物流信息 |
| 调用工具 | `mock_order_tool` |
| 读取字段 | `user_message`, `intent` |
| 写入字段 | `skill_result` |

**执行逻辑（伪代码）：**

```python
def logistics_skill(state):
    order = mock_order_tool.get_mock_order_info()
    return {
        "skill_result": {
            "action": "logistics_query",
            "order_info": {
                "order_id": order["order_id"],
                "status": order["status"],
                "tracking_no": order["tracking_no"],
                "eta": order["eta"],
            },
            "message": "已查询 mock 物流信息",
        }
    }
```

### 4. refund_skill — 退款处理

| 项目 | 说明 |
|------|------|
| 触发条件 | `intent = "refund_request"` |
| 职责 | 处理退款请求，根据 `policy_decision` 执行挽留或退款 |
| 调用策略 | 不直接调用 policy；policy 由 `route_to_skill` 调用 |
| 读取字段 | `user_message`, `intent`, `policy_decision` |
| 写入字段 | `skill_result` |

**执行逻辑（伪代码）：**

```python
def refund_skill(state):
    # route_to_skill 已先调用了 refund_policy 并写入了 policy_decision
    decision = state["policy_decision"]  # 读取 policy 决策结果
    return {
        "skill_result": {
            "action": decision,
        }
    }
```

### 5. exchange_skill — 换货处理

| 项目 | 说明 |
|------|------|
| 触发条件 | `intent = "exchange_request"` |
| 职责 | 处理换货请求 |
| 读取字段 | `user_message`, `intent` |
| 写入字段 | `skill_result` |

**执行逻辑（伪代码）：**

```python
def exchange_skill(state):
    return {
        "skill_result": {
            "action": "exchange_initiated",
            "message": "换货流程已启动，请将商品寄回",
        }
    }
```

### 6. complaint_skill — 投诉处理

| 项目 | 说明 |
|------|------|
| 触发条件 | `intent = "complaint"` |
| 职责 | 记录投诉信息，准备转人工 |
| 读取字段 | `user_message`, `intent` |
| 写入字段 | `skill_result` |

**执行逻辑（伪代码）：**

```python
def complaint_skill(state):
    return {
        "skill_result": {
            "complaint_recorded": True,
            "message": "投诉已记录，将为您转接人工客服",
        }
    }
```

### 7. human_skill — 人工处理

| 项目 | 说明 |
|------|------|
| 触发条件 | `intent = "human_request"` |
| 职责 | 处理用户明确要求人工的情况 |
| 读取字段 | `user_message`, `intent` |
| 写入字段 | `skill_result` |

**执行逻辑（伪代码）：**

```python
def human_skill(state):
    return {
        "skill_result": {
            "action": "transfer_to_human",
            "message": "正在为您转接人工客服",
        }
    }
```

### smalltalk 的特殊处理

`intent = "smalltalk"` 时，不路由到任何 skill。`route_to_skill` 直接设置：

```python
result["selected_skill"] = None
result["skill_result"] = {"action": "smalltalk_fallback"}
```

---

## 四、Tool 设计

Tool 是访问外部系统的桥梁。第一版全部是 mock，不接真实 API。

**重要：Tool 只负责提供外部数据，不负责业务决策。**

### 1. mock_product_tool — 商品查询 Mock

```python
def get_product_info() -> dict:
    """返回 mock 商品信息。"""
    return {
        "product_name": "经典款运动鞋",
        "material": "透气网面 + EVA 鞋底",
        "size": "39-44码可选",
        "features": ["轻便", "防滑", "透气"],
        "suitable_scene": "日常跑步、健身、休闲穿着",
    }

def get_recommendations() -> list[dict]:
    """返回 mock 商品推荐列表。"""
    return [
        {"name": "经典款运动鞋", "price": 299},
        {"name": "轻量跑步鞋", "price": 399},
        {"name": "户外登山鞋", "price": 499},
    ]
```

返回字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `product_name` | `str` | 商品名称 |
| `material` | `str` | 材质说明 |
| `size` | `str` | 尺码范围 |
| `features` | `list[str]` | 功能特性列表 |
| `suitable_scene` | `str` | 适用场景 |

### 2. mock_order_tool — 订单查询 Mock

```python
def get_order_info() -> dict:
    """返回 mock 订单和物流信息。"""
    return {
        "order_id": "ORD-20240101-001",
        "status": "已发货",
        "tracking_no": "SF1234567890",
        "eta": "预计明天到达",
        "items": [{"name": "经典款运动鞋", "quantity": 1}],
    }
```

返回字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `order_id` | `str` | 订单号 |
| `status` | `str` | 订单状态 |
| `tracking_no` | `str` | 快递单号 |
| `eta` | `str` | 预计送达时间 |

---

## 五、Policy 设计

Policy 是确定性业务规则代码。Policy 不能交给 LLM，因为：
1. LLM 可能忽略规则
2. LLM 可能被 prompt injection 绕过
3. 规则需要可测试、可追踪

### 1. refund_policy.py — 退款规则

**规则：**

| 退款次数 | 决策 | 说明 |
|---------|------|------|
| 第一次退款请求 | `retention` | 先挽留，了解原因 |
| 第二次明确退款请求 | `refund_workflow` | 执行退款流程 |
| 第三次退款请求 | `direct_refund_or_human_confirm` | 直接退款或人工确认 |

**为什么不能把退款规则写进 prompt：**

```
❌ 错误做法：
  system_prompt = "如果用户第一次要求退款，先挽留……"
  → LLM 可能忽略、可能被绕过、无法单元测试

✅ Agent Harness 做法：
  refund_policy.decide_refund_action(refund_count)
  → 确定性的代码逻辑，可测试、不可绕过
```

**第一版策略：**

Phase 5 中 `refund_count` 暂时 mock 为 1（首次退款），所以第一版总是返回 `retention`。后续 Phase 可以改为从 Memory 读取真实退款次数。

**State 只保存决策结果：**

```python
state["policy_decision"] = "retention"
# 不保存复杂的退款规则逻辑在 state 中
```

### 2. escalation_policy.py — 转人工规则

**规则（满足任一条件则转人工）：**

| 条件 | 说明 |
|------|------|
| `emotion_score > 0.85` | 情绪非常激动，如 angry（0.90） |
| `intent = "human_request"` | 用户明确要求人工 |
| `intent = "complaint"` | 投诉必须人工处理 |
| `errors` 不为空 | 系统出现问题需要人工介入 |

**转人工判断逻辑（伪代码）：**

```python
def should_escalate(emotion_score, intent, errors) -> tuple[bool, str]:
    reasons = []

    if emotion_score > 0.85:
        reasons.append("用户情绪评分过高")
    if intent == "human_request":
        reasons.append("用户要求转人工")
    if intent == "complaint":
        reasons.append("投诉需要人工处理")
    if errors:
        reasons.append(f"系统错误：{errors}")

    if reasons:
        return True, "；".join(reasons)
    return False, ""
```

**Phase 4 和 Phase 5 的区别：**

| 阶段 | need_human | 说明 |
|------|-----------|------|
| Phase 4 | 始终 `False` | 分类阶段不处理转人工 |
| Phase 5 | 由 `escalation_policy` 决定 | `need_human` 开始真正生效 |

---

## 六、route_to_skill 设计

### 职责

`route_to_skill` 是 Phase 5 的核心节点，它根据 `intent` 选择对应的 skill 并执行。

### 映射关系

| intent | 调用的 skill | selected_skill 值 |
|--------|-------------|-------------------|
| `product_question` | `product_qa_skill()` | `"product_qa_skill"` |
| `recommendation` | `recommendation_skill()` | `"recommendation_skill"` |
| `logistics_question` | `logistics_skill()` | `"logistics_skill"` |
| `refund_request` | `refund_skill()` | `"refund_skill"` |
| `exchange_request` | `exchange_skill()` | `"exchange_skill"` |
| `complaint` | `complaint_skill()` | `"complaint_skill"` |
| `human_request` | `human_skill()` | `"human_skill"` |
| `smalltalk` | 不调用任何 skill | `None` |

### 执行逻辑（伪代码）

```python
from datetime import datetime

from app.policies.refund_policy import decide_refund_action
from app.skills.product_qa_skill import product_qa_skill
from app.skills.recommendation_skill import recommendation_skill
from app.skills.logistics_skill import logistics_skill
from app.skills.refund_skill import refund_skill
from app.skills.exchange_skill import exchange_skill
from app.skills.complaint_skill import complaint_skill
from app.skills.human_skill import human_skill


def route_to_skill(state):
    intent = state["intent"]

    # intent → skill 映射
    route_map = {
        "product_question": product_qa_skill,
        "recommendation": recommendation_skill,
        "logistics_question": logistics_skill,
        "refund_request": refund_skill,
        "exchange_request": exchange_skill,
        "complaint": complaint_skill,
        "human_request": human_skill,
    }

    result = {}

    if intent in route_map:
        # route_to_skill 设置 selected_skill（skill 名称）
        skill_name_map = {
            "product_question": "product_qa_skill",
            "recommendation": "recommendation_skill",
            "logistics_question": "logistics_skill",
            "refund_request": "refund_skill",
            "exchange_request": "exchange_skill",
            "complaint": "complaint_skill",
            "human_request": "human_skill",
        }
        result["selected_skill"] = skill_name_map[intent]

        # 如果 intent 是 refund_request，先调用 refund_policy
        if intent == "refund_request":
            decision = decide_refund_action(refund_count=1)
            result["policy_decision"] = decision.value

        # 调用 skill 函数，获取 skill_result
        skill_func = route_map[intent]
        skill_output = skill_func(state)
        result["skill_result"] = skill_output["skill_result"]
    else:
        # smalltalk 或未识别兜底
        result["selected_skill"] = None
        result["skill_result"] = {"action": "smalltalk_fallback"}

    updated_logs = list(state["logs"])
    updated_logs.append({
        "node": "route_to_skill",
        "summary": f"selected_skill={result['selected_skill']}",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })
    result["logs"] = updated_logs

    return result
```

### 设计原则

1. **第一版把 skill 调用放在 route_to_skill 中** — 不引入复杂 conditional edge，保持简单
2. **每个 skill 是一个独立函数** — 后续可以拆成独立的 LangGraph 节点
3. **smalltalk 不调用任何 skill** — 避免闲聊触发不必要的业务逻辑

---

## 七、State 字段读写关系

### route_to_skill

| 方向 | 字段 | 说明 |
|------|------|------|
| 读取 | `intent` | 选择调用的 skill |
| 读取 | `user_message` | 传给 skill 的上下文 |
| 读取 | `emotion` | 传给 skill 的情绪上下文 |
| 读取 | `customer_stage` | 传给 skill 的阶段上下文 |
| 写入 | `selected_skill` | 记录调用了哪个 skill |
| 写入 | `skill_result` | skill 执行结果 |
| 写入 | `policy_decision` | （refund_skill 时写入） |
| 写入 | `logs` | 执行记录 |

### escalation_check

| 方向 | 字段 | 说明 |
|------|------|------|
| 读取 | `intent` | 判断是否为 complaint / human_request |
| 读取 | `emotion_score` | 判断是否 > 0.85 |
| 读取 | `errors` | 判断是否有系统错误 |
| 写入 | `need_human` | True / False |
| 写入 | `human_reason` | 转人工的原因 |
| 写入 | `logs` | 执行记录 |

### 各 skill

| 方向 | 字段 | 说明 |
|------|------|------|
| 读取 | `user_message` | 用户输入，skill 执行的上下文 |
| 读取 | `intent` | skill 触发的依据 |
| 读取 | `customer_stage` | 客户阶段，部分 skill 可能用到 |
| 写入 | `skill_result` | 执行结果 dict |

### 各 policy

| 方向 | 字段 | 说明 |
|------|------|------|
| 读取 | `intent` | 判断是否为 refund_request |
| 读取 | `emotion_score` | 判断是否 > 0.85 |
| 读取 | `errors` | 判断是否不为空 |
| 读取 | `refund_count` | 退款次数（Phase 5 mock 为 1） |
| 写入 | `policy_decision` | 退款决策结果 |
| 写入 | `need_human` | 转人工决策结果 |
| 写入 | `human_reason` | 转人工原因 |

---

## 八、示例输入输出

### 示例 1：物流查询

```
输入： "我的快递怎么还没到"

intent          = logistics_question
selected_skill  = "logistics_skill"
skill_result    = {
    "order_id": "ORD-20240101-001",
    "status": "已发货",
    "tracking_no": "SF1234567890",
    "eta": "预计明天到达"
}
need_human      = false
emotion_score   = 0.65    ← 不触发转人工
```

### 示例 2：首次退款挽留（触发转人工）

```
输入： "质量太差了我要退款"

intent          = refund_request
selected_skill  = "refund_skill"
policy_decision = "retention"
skill_result    = {
    "action": "retention",
    "message": "首次退款请求，先挽留"
}
need_human      = true    ← emotion_score=0.9 > 0.85，触发转人工
human_reason    = "用户情绪评分过高"
```

### 示例 3：商品咨询

```
输入： "这个衣服是什么材质"

intent          = product_question
selected_skill  = "product_qa_skill"
skill_result    = {
    "product_name": "经典款运动鞋",
    "material": "透气网面 + EVA 鞋底",
    "size": "39-44码可选"
}
need_human      = false
```

### 示例 4：要求转人工

```
输入： "我要人工，太生气了"

intent          = human_request
selected_skill  = "human_skill"
skill_result    = {
    "action": "transfer_to_human",
    "message": "正在为您转接人工客服"
}
need_human      = true
human_reason    = "用户要求转人工；用户情绪评分过高"
```

### 示例 5：投诉

```
输入： "你们这个太垃圾了，我要投诉"

intent          = complaint
selected_skill  = "complaint_skill"
skill_result    = {
    "complaint_recorded": True,
    "message": "投诉已记录，将为您转接人工客服"
}
need_human      = true
human_reason    = "投诉需要人工处理"
```

### 示例 6：换货

```
输入： "我要换个尺码"

intent          = exchange_request
selected_skill  = "exchange_skill"
skill_result    = {
    "action": "exchange_initiated",
    "message": "换货流程已启动，请将商品寄回"
}
need_human      = false
```

---

## 九、Phase 5.2 实现边界

### 允许修改的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/nodes/route_to_skill.py` | **重写** | intent→skill 路由 + 执行 |
| `app/nodes/escalation_check.py` | **重写** | 调用 escalation_policy 判断 |
| `app/skills/product_qa_skill.py` | **重写** | 商品问答 skill |
| `app/skills/recommendation_skill.py` | **重写** | 商品推荐 skill |
| `app/skills/logistics_skill.py` | **重写** | 物流查询 skill |
| `app/skills/refund_skill.py` | **重写** | 退款处理 skill，调用 refund_policy |
| `app/skills/exchange_skill.py` | **重写** | 换货处理 skill |
| `app/skills/complaint_skill.py` | **重写** | 投诉处理 skill |
| `app/skills/human_skill.py` | **重写** | 人工处理 skill |
| `app/tools/mock_product_tool.py` | **重写** | 商品查询 mock |
| `app/tools/mock_order_tool.py` | **重写** | 订单查询 mock |
| `app/policies/refund_policy.py` | 补充完善 | 退款规则 |
| `app/policies/escalation_policy.py` | 补充完善 | 转人工规则 |
| `app/graph.py` | **更新** | 注册 route_to_skill 和 escalation_check |
| `app/main.py` | **更新** | 展示 skill_result 和 need_human |
| `tests/test_skills_policies.py` | **新建** | 测试 |

### 不得修改的文件

| 文件 | 原因 |
|------|------|
| `docs/STATE_DESIGN.md` | State 设计已定稿 |
| `docs/GRAPH_DESIGN.md` | 图基础结构已定稿 |
| `docs/CLASSIFICATION_DESIGN.md` | 分类设计已定稿 |
| `app/state/customer_state.py` | State 定义已定稿，除非发现必须修正的问题 |

---

## 十、Phase 5.2 验收标准

实现后必须满足：

| # | 验收项 | 验证方式 |
|---|--------|---------|
| 1 | `.venv/bin/python -m app.main` 可运行 | 直接运行 |
| 2 | `.venv/bin/python -m pytest` 全部通过 | 运行测试 |
| 3 | "我的快递怎么还没到" → `selected_skill` = `"logistics_skill"` | 测试断言 |
| 4 | "我的快递怎么还没到" → `skill_result` 包含物流信息 | 测试断言 |
| 5 | "质量太差了我要退款" → `selected_skill` = `"refund_skill"` | 测试断言 |
| 6 | "质量太差了我要退款" → `policy_decision` = `"retention"` | 测试断言 |
| 7 | "这个衣服是什么材质" → `selected_skill` = `"product_qa_skill"` | 测试断言 |
| 8 | "这个衣服是什么材质" → `skill_result` 包含商品信息 | 测试断言 |
| 9 | "我要人工，太生气了" → `selected_skill` = `"human_skill"` | 测试断言 |
| 10 | "我要人工，太生气了" → `need_human` = `True` | 测试断言 |
| 11 | "你们这个太垃圾了，我要投诉" → `selected_skill` = `"complaint_skill"` | 测试断言 |
| 12 | "你们这个太垃圾了，我要投诉" → `need_human` = `True` | 测试断言 |
| 13 | `logs` 包含 `route_to_skill` 和 `escalation_check` | 测试断言 |
| 14 | 没有接真实 API | 代码审查 |
| 15 | LLM 没有直接做退款决策 | 代码审查 |
| 16 | 退款规则没有写进 prompt | 代码审查 |

---

## 十一、不要过度设计

Phase 5 明确不做的事：

| 不做 | 原因 |
|------|------|
| **不接真实订单 API** | 第一版全部 mock，mock 验证通过后才考虑接入 |
| **不接真实商品库** | 同上 |
| **不接 Dify** | 第一版不依赖外部 AI 平台 |
| **不接数据库** | 数据在 State 中流转即可 |
| **不接飞书** | 第一版不需要 IM 集成 |
| **不做真实退款** | 不涉及真实资金操作 |
| **不做复杂多轮记忆** | 每个会话独立处理 |
| **不做 generate_reply** | 留到 Phase 6 |
| **不做复杂 conditional edge** | route_to_skill 直接调用 skill 函数 |
| **不把 refund_count 接入真实系统** | Phase 5 mock 为 1 |

---

> **下一阶段建议**：进入 **Phase 5.2**，根据本文档实现 route_to_skill、escalation_check、7 个 skill、2 个 mock tool、2 个 policy。
