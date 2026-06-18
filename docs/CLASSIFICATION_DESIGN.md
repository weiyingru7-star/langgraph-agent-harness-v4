# 分类节点设计 — CLASSIFICATION_DESIGN

> **Phase 4.1 · 设计文档**
> 本文档只做设计讨论，不涉及代码实现。

---

## 一、为什么 Phase 4 要加入分类节点

### 当前阶段的问题

到 Phase 3 为止，最小 LangGraph 流程已经跑通，State 可以在 4 个节点之间正常流转。但目前的流程只做了两件事：

1. **判断输入类型**（modality）— 纯文本还是图文
2. **文本摘要**（text_analysis）— mock 分析

State 中的 `intent`、`emotion`、`emotion_score`、`customer_stage` 还是默认值，**没有任何业务价值**。

```
当前 State 输出：
  intent         = None         ← 不知道用户想干什么
  emotion        = "neutral"    ← 默认值
  emotion_score  = 0.0          ← 默认值
  customer_stage = "unknown"    ← 默认值
```

### Phase 4 要解决的问题

加入三个分类节点后，流程可以输出有业务意义的分类结果：

```
加入后 State 输出：
  intent         = "refund_request"     ← 知道用户想退款
  emotion        = "angry"              ← 知道用户很生气
  emotion_score  = 0.85                 ← 可以计算情绪评分
  customer_stage = "after_sale"         ← 知道用户在售后阶段
```

这些分类结果是后续路由、策略、回复的**关键输入**。

### 为什么现在做分类

| 理由 | 说明 |
|------|------|
| **为路由做准备** | `intent` 是 `route_to_skill` 的核心输入，没有它就没办法路由 |
| **为 Policy 做准备** | `emotion_score` 是 `escalation_policy` 的判断依据 |
| **为回复生成做准备** | `intent` + `emotion` 决定回复的语气和内容 |
| **独立可测试** | 每个分类节点可以单独测试，不依赖后续模块 |

---

## 二、三个节点分别负责什么

### 整体位置

```
START → parse_input → decide_modality → analyze_text
                                          ↓
                                     classify_intent   ← 新增
                                          ↓
                                     classify_emotion  ← 新增
                                          ↓
                                     classify_stage    ← 新增
                                          ↓
                                     save_log → END
```

### 节点职责一览

| 节点 | 核心问题 | 输入 | 输出 |
|------|---------|------|------|
| `classify_intent` | 用户想做什么？ | `user_message` | `intent`, `intent_confidence` |
| `classify_emotion` | 用户情绪如何？ | `user_message` | `emotion`, `emotion_score` |
| `classify_stage` | 用户在哪个阶段？ | `intent` | `customer_stage` |

### 三个节点的关系

```
user_message
     │
     ├─→ classify_intent    → intent + intent_confidence
     │
     ├─→ classify_emotion   → emotion + emotion_score
     │                          │
     │                     （互不依赖，可以独立工作）
     │
     └─→ classify_stage     → customer_stage
                                ↑ 依赖 intent
```

**关键设计决策**：
- `classify_intent` 和 `classify_emotion` **互不依赖**，各自独立分析 `user_message`
- `classify_stage` **依赖 `intent`** 的结果，因为客户阶段由意图推导而来
- 三个节点**都不依赖 `text_analysis`**，保持职责边界清晰

---

## 三、每个节点读哪些 State 字段、写哪些 State 字段

### classify_intent

| 方向 | 字段 | 说明 |
|------|------|------|
| 读取 | `user_message` | 用户输入的文本，用于关键词匹配 |
| 写入 | `intent` | 识别出的意图（字符串枚举） |
| 写入 | `intent_confidence` | 匹配置信度（0.0~1.0），关键词命中越高越确定 |
| 写入 | `logs` | 追加一条执行记录 |

**设计原则**：
- 只依赖 `user_message`，不依赖 `text_analysis`
- 第一版用**关键词规则**实现，后续升级为 LLM 调用
- 关键词规则的本质是一个 **关键词 → intent** 的映射表，加上匹配逻辑

### classify_emotion

| 方向 | 字段 | 说明 |
|------|------|------|
| 读取 | `user_message` | 用户输入的文本，用于情绪关键词匹配 |
| 写入 | `emotion` | 识别出的情绪标签（字符串枚举） |
| 写入 | `emotion_score` | 情绪评分（0.0~1.0），映射规则见下文 |
| 写入 | `logs` | 追加一条执行记录 |

**设计原则**：
- 第一版用**关键词规则**实现
- `emotion_score` 由 `emotion` 标签映射而来，不是独立计算
- 后续升级为 LLM 后，`emotion_score` 可直接由 LLM 判断

### classify_stage

| 方向 | 字段 | 说明 |
|------|------|------|
| 读取 | `intent` | 已识别出的意图，用于推导客户阶段 |
| 写入 | `customer_stage` | 客户所处阶段（字符串枚举） |
| 写入 | `logs` | 追加一条执行记录 |

**设计原则**：
- 依赖 `intent`，不直接分析 `user_message`
- 是一个**纯映射**逻辑：intent → stage
- 后续升级 LLM 后，可以改为直接分析 `user_message`（不依赖 intent）

---

## 四、intent 的关键词规则和优先级

### 匹配逻辑（伪代码）

```python
def classify_intent(user_message: str) -> tuple[str, float]:
    """根据关键词匹配用户意图。

    策略：
    1. 从高优先级到低优先级遍历关键词组
    2. 第一个命中的关键词组即为意图
    3. 命中关键词越多 → confidence 越高
    """
    # 优先级从高到低
    rules = [
        ("human_request",      0.95, ["人工", "转人工", "找客服"]),
        ("complaint",          0.95, ["投诉", "举报", "差评"]),
        ("refund_request",     0.90, ["退款", "退钱", "退货"]),
        ("exchange_request",   0.85, ["换货", "换一个", "换个"]),
        ("logistics_question", 0.80, ["物流", "快递", "发货", "到哪了",
                                      "配送", "还没到"]),
        ("recommendation",     0.75, ["推荐", "建议", "哪个好", "有什么"]),
        ("product_question",   0.70, ["多少钱", "价格", "尺寸", "颜色",
                                      "怎么用", "功能"]),
    ]

    for intent, confidence, keywords in rules:
        if any(kw in user_message for kw in keywords):
            return intent, confidence

    # 默认兜底：没有命中任何关键词 → 闲聊
    return "smalltalk", 0.30
```

### 优先级规则

| 优先级 | intent | 触发关键词 | 基础置信度 | 为什么高优先级 |
|--------|--------|-----------|-----------|--------------|
| 1 | `human_request` | 人工、转人工、找客服 | 0.95 | 用户明确要求转人工，必须优先响应 |
| 2 | `complaint` | 投诉、举报、差评 | 0.95 | 投诉需要特殊处理流程 |
| 3 | `refund_request` | 退款、退钱、退货 | 0.90 | 退款决策需要 Policy 介入 |
| 4 | `exchange_request` | 换货、换一个、换个 | 0.85 | 换货和退款走不同流程 |
| 5 | `logistics_question` | 物流、快递、发货、到哪了、配送、还没到 | 0.80 | 物流查询是最常见的客服场景之一 |
| 6 | `recommendation` | 推荐、建议、哪个好、有什么 | 0.75 | 推荐需要商品知识 |
| 7 | `product_question` | 多少钱、价格、尺寸、颜色、怎么用、功能 | 0.70 | 商品咨询是最基础的客服场景 |
| 8 | `smalltalk` | 默认兜底（无关键词命中） | 0.30 | 其他所有情况，置信度低 |

### 优先级设计的原因

- **高优先级意图**通常是用户**明确表达**的（"转人工"、"投诉"、"退款"）
- **低优先级意图**通常是用户**模糊表达**或**中性询问**（"多少钱"、"推荐"）
- 如果用户同时说了"投诉"和"退款"，取高优先级的 `complaint`
- `smalltalk` 作为兜底，避免返回 `None`

### 升级到 LLM 的路径

```python
# 当前（Phase 4）：
def classify_intent(user_message):
    return keyword_match(user_message)   # 关键词版本

# 未来（接入真实 LLM 后）：
def classify_intent(user_message):
    return llm_call(user_message)        # LLM 版本

# 调用方完全不受影响——接口相同，返回相同格式
```

---

## 五、emotion 的关键词规则和优先级

### 匹配逻辑（伪代码）

```python
def classify_emotion(user_message: str) -> tuple[str, float]:
    """根据关键词匹配用户情绪。

    策略：从高优先级到低优先级遍历关键词组。
    """
    rules = [
        ("angry",        0.90, ["太差", "垃圾", "气死", "愤怒", "很差",
                                "什么破", "骗子"]),
        ("urgent",       0.85, ["马上", "立刻", "赶紧", "急", "快点"]),
        ("anxious",      0.80, ["担心", "怎么办", "还没", "还不", "多久"]),
        ("disappointed", 0.75, ["失望", "太差了", "不好", "不行", "差劲"]),
    ]

    for emotion, score, keywords in rules:
        if any(kw in user_message for kw in keywords):
            return emotion, score

    return "neutral", 0.0
```

### 优先级规则

| 优先级 | emotion | 触发关键词 | emotion_score | 说明 |
|--------|---------|-----------|--------------|------|
| 1 | `angry` | 太差、垃圾、气死、愤怒、很差、什么破、骗子 | 0.90 | 愤怒情绪需要优先处理 |
| 2 | `urgent` | 马上、立刻、赶紧、急、快点 | 0.85 | 急迫情绪需要快速响应 |
| 3 | `anxious` | 担心、怎么办、还没、还不、多久 | 0.80 | 焦虑情绪需要安抚 |
| 4 | `disappointed` | 失望、太差了、不好、不行、差劲 | 0.75 | 失望情绪需要解释 |
| 5 | `neutral` | 默认兜底（无关键词命中） | 0.0 | 平静状态 |

### emotion_score 和转人工的关系

```
emotion_score > 0.85  → 触发转人工（escalation_policy 判断）
```

当前映射：
- `angry`（0.90）→ 触发转人工
- `urgent`（0.85）→ **不触发**（0.85 需要 **大于** 0.85，不是大于等于）
- `anxious`（0.80）→ 不触发
- `disappointed`（0.75）→ 不触发
- `neutral`（0.0）→ 不触发

### 升级到 LLM 的路径

```python
# 当前（Phase 4）：
def classify_emotion(user_message):
    return keyword_match(user_message)    # 关键词版本

# 未来（接入真实 LLM 后）：
def classify_emotion(user_message):
    llm_result = llm_call(user_message)   # LLM 版本
    return llm_result.emotion, llm_result.emotion_score
```

---

## 六、customer_stage 的判断规则

### 映射逻辑（伪代码）

```python
def classify_stage(intent: str) -> str:
    """根据 intent 推导客户阶段。

    这是一个纯映射，没有关键词分析。
    """
    mapping = {
        "product_question":     "pre_sale",    # 咨询商品 → 售前
        "recommendation":       "pre_sale",    # 寻求推荐 → 售前

        "logistics_question":   "in_sale",     # 物流查询 → 售中

        "refund_request":       "after_sale",  # 退款 → 售后
        "exchange_request":     "after_sale",  # 换货 → 售后
        "complaint":            "after_sale",  # 投诉 → 售后

        "human_request":        "unknown",     # 转人工 → 无法确定阶段
        "smalltalk":            "unknown",     # 闲聊 → 无法确定阶段
    }

    return mapping.get(intent, "unknown")
```

### 映射规则表

| intent | customer_stage | 理由 |
|--------|---------------|------|
| `product_question` | `pre_sale` | 咨询商品，还没下单 |
| `recommendation` | `pre_sale` | 寻求推荐，还没下单 |
| `logistics_question` | `in_sale` | 询问物流，已经下单 |
| `refund_request` | `after_sale` | 要退款，已经收货 |
| `exchange_request` | `after_sale` | 要换货，已经收货 |
| `complaint` | `after_sale` | 投诉，通常是售后问题 |
| `human_request` | `unknown` | 要求转人工，阶段不确定 |
| `smalltalk` | `unknown` | 闲聊，阶段不确定 |

---

## 七、输入输出示例（8 个）

### 示例 1：商品咨询

| 字段 | 值 |
|------|-----|
| user_message | "这件衣服多少钱" |
| intent | `product_question` (0.70) |
| emotion | `neutral` (0.0) |
| customer_stage | `pre_sale` |

### 示例 2：寻求推荐

| 字段 | 值 |
|------|-----|
| user_message | "推荐一款好用的手机" |
| intent | `recommendation` (0.75) |
| emotion | `neutral` (0.0) |
| customer_stage | `pre_sale` |

### 示例 3：物流查询（焦虑）

| 字段 | 值 |
|------|-----|
| user_message | "我的快递还没到，怎么办" |
| intent | `logistics_question` (0.80) |
| emotion | `anxious` (0.80) |
| customer_stage | `in_sale` |

### 示例 4：催促发货（急迫）

| 字段 | 值 |
|------|-----|
| user_message | "马上发货！急死了" |
| intent | `logistics_question` (0.80) |
| emotion | `urgent` (0.85) |
| customer_stage | `in_sale` |

### 示例 5：退款请求（愤怒）

| 字段 | 值 |
|------|-----|
| user_message | "质量太差了我要退款" |
| intent | `refund_request` (0.90) |
| emotion | `angry` (0.90) |
| customer_stage | `after_sale` |

### 示例 6：换货请求（失望）

| 字段 | 值 |
|------|-----|
| user_message | "这个破了能换一个吗" |
| intent | `exchange_request` (0.85) |
| emotion | `disappointed` (0.75) |
| customer_stage | `after_sale` |

### 示例 7：投诉（愤怒）

| 字段 | 值 |
|------|-----|
| user_message | "我要投诉你们，客服态度太差了" |
| intent | `complaint` (0.95) |
| emotion | `angry` (0.90) |
| customer_stage | `after_sale` |

### 示例 8：闲聊

| 字段 | 值 |
|------|-----|
| user_message | "你好" |
| intent | `smalltalk` (0.30) |
| emotion | `neutral` (0.0) |
| customer_stage | `unknown` |

---

## 八、Phase 4.2 实现边界

### 允许修改的文件

| 文件 | 修改内容 |
|------|---------|
| `app/nodes/classify_intent.py` | 新建：关键词匹配实现 |
| `app/nodes/classify_emotion.py` | 新建：关键词匹配实现 |
| `app/nodes/classify_stage.py` | 新建：intent→stage 映射实现 |
| `app/graph.py` | 在 `analyze_text` 和 `save_log` 之间插入三个节点 |
| `app/main.py` | 更新 demo 输出，展示分类结果 |
| `tests/test_classification.py` | 新增：测试分类逻辑 |

### 每个节点的具体实现要求

#### classify_intent

```python
from app.state.customer_state import (
    INTENT_COMPLAINT, INTENT_EXCHANGE_REQUEST,
    INTENT_HUMAN_REQUEST, INTENT_LOGISTICS_QUESTION,
    INTENT_PRODUCT_QUESTION, INTENT_RECOMMENDATION,
    INTENT_REFUND_REQUEST, INTENT_SMALLTALK,
    CustomerServiceState,
)


def classify_intent(state: CustomerServiceState) -> dict:
    """关键词匹配用户意图。"""
    text = state["user_message"]
    # ... 关键词匹配逻辑 ...
    return {"intent": intent, "intent_confidence": confidence, "logs": updated_logs}
```

#### classify_emotion

```python
from app.state.customer_state import (
    EMOTION_ANGRY, EMOTION_ANXIOUS, EMOTION_DISAPPOINTED,
    EMOTION_NEUTRAL, EMOTION_URGENT,
    CustomerServiceState,
)


def classify_emotion(state: CustomerServiceState) -> dict:
    """关键词匹配用户情绪。"""
    text = state["user_message"]
    # ... 关键词匹配逻辑 ...
    return {"emotion": emotion, "emotion_score": score, "logs": updated_logs}
```

#### classify_stage

```python
def classify_stage(state: CustomerServiceState) -> dict:
    """根据 intent 推导客户阶段。"""
    intent = state["intent"]
    stage = STAGE_UNKNOWN
    # ... intent→stage 映射 ...
    return {"customer_stage": stage, "logs": updated_logs}
```

### 不得修改的文件

| 文件 | 为什么不能改 |
|------|-------------|
| `app/skills/*` | Phase 5 才涉及 skill |
| `app/tools/*` | Phase 5 才涉及 tool |
| `app/policies/*` | Phase 5 才涉及 policy |
| `app/memory/*` | 分类阶段不需要记忆 |
| `docs/STATE_DESIGN.md` | State 设计已定稿 |
| `docs/GRAPH_DESIGN.md` | 图基础结构已定稿 |

---

## 九、Phase 4.2 验收标准

### 9.1 可运行

```bash
.venv/bin/python -m app.main
```

### 9.2 验收检查清单

| # | 验收项 | 状态 |
|---|--------|------|
| 1 | `.venv/bin/python -m app.main` 可运行 | ⬜ |
| 2 | `intent` 不再为 `None`，根据关键词正确匹配 | ⬜ |
| 3 | `intent_confidence` 随之正确设置 | ⬜ |
| 4 | `emotion` 根据关键词正确识别 | ⬜ |
| 5 | `emotion_score` 根据 emotion 正确映射 | ⬜ |
| 6 | `customer_stage` 根据 intent 正确推导 | ⬜ |
| 7 | `logs` 包含 `classify_intent`、`classify_emotion`、`classify_stage` | ⬜ |
| 8 | 无关键词时：`smalltalk` + `neutral` + `unknown` | ⬜ |
| 9 | `pytest` 全部通过 | ⬜ |

### 9.3 测试要求

测试 `tests/test_classification.py` 至少覆盖：

- 每个 intent 至少有一个测试用例
- 每个 emotion 至少有一个测试用例
- 每个 customer_stage 至少有一个测试用例
- 空输入走兜底逻辑
- 无关键词走默认值

---

## 十、为什么本阶段还不做 route_to_skill、skill、policy、conditional edge

| 不做 | 原因 |
|------|------|
| **route_to_skill** | 分类结果还没有验证过是否可靠。先验证分类准确，再做路由 |
| **skill** | skill 需要 `intent` 作为输入，但分类的结果需要先用单元测试验证 |
| **policy** | policy 需要 `emotion_score` 和 `refund_count`，`refund_count` 还没有实现 |
| **conditional edge** | Phase 4 只有线性串行节点，没有需要分支的条件 |
| **真实 LLM** | 先用关键词验证分类逻辑，后续接 LLM 时接口不变 |

### Phase 5 计划（后续阶段）

```
Phase 5 流程预览：
  START → parse_input → decide_modality → analyze_text
         → classify_intent → classify_emotion → classify_stage
         → route_to_skill       ← 新增（条件边）
         → refund_skill / logistics_skill / ...  ← 新增（skill 节点）
         → generate_reply        ← 新增
         → escalation_check      ← 新增（policy）
         → save_log → END
```

---

> **下一阶段建议**：进入 **Phase 4.2**，根据本文档实现 `classify_intent`、`classify_emotion`、`classify_stage` 三个节点。
