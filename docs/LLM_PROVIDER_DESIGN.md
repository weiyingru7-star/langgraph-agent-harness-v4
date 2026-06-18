# LLM Provider 接入设计 — LLM_PROVIDER_DESIGN

> **Phase 10.11 · 设计文档**
> 目标：设计一个可控、可测试、可回退的 LLM Provider 层，为后续 LLM 回复润色做准备。

---

## 一、为什么要接 LLM Provider

### 当前短板

| 问题 | 现状 | 影响 |
|------|------|------|
| 回复生硬 | 模板字符串拼接 | 像机器人，不像真人客服 |
| 关键词维护成本高 | `classify_intent` 关键词列表不断增长 | 改不动、测不完 |
| 没有语义兜底 | 未命中关键词就回 smalltalk | 用户困惑 |
| 不支持语气调整 | `emotion=angry` 和 `emotion=neutral` 回复一样 | 不专业 |

### LLM 增强价值

```
之前：关键词匹配 → 模板回复 → "您咨询的商品信息如下：…"
之后：关键词匹配 → 模板回复 → LLM 润色 → "这款防晒衣采用锦纶混纺面料，透气性很不错～"

之前："有什么码数" → 没命中 → "您好，我在的"
之后：Context Loader + LLM → 知道在问防晒衣尺码 → 自然回答
```

---

## 二、Provider 架构

```
app/llm/
├── __init__.py
├── base.py               # 统一接口
├── mock_provider.py       # 测试用 mock
├── deepseek_provider.py   # 真实 API provider
├── provider_factory.py    # 根据配置选择 provider
└── safety.py              # 输出安全检查
```

### base.py — 统一接口

```python
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseLLMProvider(ABC):
    """LLM Provider 统一接口。"""

    @abstractmethod
    def generate_reply(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成或润色回复。

        Args:
            payload: 包含 user_message, intent, emotion, skill_result,
                     policy_decision, conversation_history, template_reply 等

        Returns:
            {"reply": str}  — 正常
            {"error": str}  — 失败，由调用方 fallback
        """
```

### mock_provider.py

```python
class MockLLMProvider(BaseLLMProvider):
    """测试用 mock，不调用真实 API。"""

    def generate_reply(self, payload: dict) -> dict:
        return {"reply": payload.get("template_reply", "")}
```

### deepseek_provider.py

```python
class DeepSeekProvider(BaseLLMProvider):
    """真实 DeepSeek API Provider。"""

    def generate_reply(self, payload: dict) -> dict:
        # 调用 DeepSeek API
        # ...
```

### provider_factory.py

```python
_PROVIDERS = {
    "mock": MockLLMProvider,
    "deepseek": DeepSeekProvider,
}

def get_provider(name: str | None = None) -> BaseLLMProvider:
    provider_name = name or os.getenv("LLM_PROVIDER", "mock")
    cls = _PROVIDERS.get(provider_name)
    if not cls:
        return MockLLMProvider()
    return cls()
```

---

## 三、环境变量设计

```bash
# .env.example

# LLM Provider 配置（默认 mock，不调用真实 API）
LLM_PROVIDER=mock

# DeepSeek API（仅在 LLM_PROVIDER=deepseek 时需要）
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 超时和安全
LLM_TIMEOUT_SECONDS=15

# 功能开关（默认关闭）
LLM_ENABLE_REPLY_POLISH=false
```

### 安全规则

```
❌ API key 不能写进代码
❌ .env 不提交 Git
✅ 默认 LLM_PROVIDER=mock，不调用任何 API
✅ LLM_ENABLE_REPLY_POLISH=false，不开启润色
```

---

## 四、LLM 能做什么 / 不能做什么

### 允许

| 用途 | 说明 |
|------|------|
| 润色客服回复 | 基于 template_reply 做文字润色 |
| 根据 emotion 调整语气 | angry 语气更温和，neutral 保持正常 |
| 承接上下文 | 参考 conversation_history 自然承接 |
| 组织 skill_result | 把结构化数据整理成自然语言 |
| 知识不足时追问 | "您能再具体描述一下问题吗？" |

### 禁止

| 禁止 | 原因 |
|------|------|
| 决定退款 | Policy 控制 |
| 承诺退款成功 | 安全风险 |
| 承诺发货 / 补发 / 补偿 | 安全风险 |
| 修改 policy_decision | 不可绕过 |
| 修改 need_human | 不可绕过 |
| 修改 selected_skill | 路由不可绕过 |
| 编造商品数据 | 知识库是唯一来源 |
| 编造物流信息 | Tool 返回是唯一来源 |
| 绕过转人工 | escalation_check 控制 |

---

## 五、输入 payload 设计

```python
payload = {
    # 用户输入
    "user_message": "这件衣服有黑色的吗",

    # Agent 分析
    "intent": "product_question",
    "emotion": "neutral",
    "emotion_score": 0.0,
    "customer_stage": "pre_sale",

    # 路由和策略
    "selected_skill": "product_qa_skill",
    "skill_result": {
        "knowledge_source": "local_products",
        "matched_product": {"name": "UPF50+ 轻薄防晒衣", ...},
    },
    "policy_decision": None,
    "need_human": False,
    "human_reason": None,

    # 上下文
    "conversation_history": [
        {"role": "user", "content": "这个衣服是什么材质"},
        {"role": "assistant", "content": "这款防晒衣采用锦纶混纺面料…"},
    ],

    # 模板回复（fallback 基础）
    "template_reply": "您咨询的商品信息如下：\n商品名称：UPF50+ 轻薄防晒衣…",

    # 安全约束
    "safety_rules": [
        "不要承诺退款",
        "不要编造商品信息",
        "不要修改 policy_decision",
        "不要承诺已发货/已补偿",
        "不要在纯图片场景下编造图片内容",
    ],
}
```

---

## 六、LLM 输出格式

### 允许的输出

```json
{
  "reply": "这款防晒衣有黑色可选～尺码从 S 到 XL 都有，黑色很百搭，您放心选。"
}
```

### 不允许的输出

```json
{
  "reply": "...",
  "policy_decision": "refund_workflow",    # ❌ 不允许
  "need_human": false,                     # ❌ 不允许
  "refund_amount": 100                     # ❌ 不允许
}
```

LLM 输出中只要包含 `policy_decision`、`need_human`、`refund`、`selected_skill` 等字段，Safety 过滤器应当拒绝并回退 template。

---

## 七、Fallback 机制

### 触发条件

| 条件 | 处理 |
|------|------|
| LLM 调用失败（网络） | 回退 `template_reply` |
| LLM 超时 | 回退 `template_reply` |
| LLM 返回空字符串 | 回退 `template_reply` |
| LLM 返回非 JSON | 回退 `template_reply` |
| Safety 拦截 | 回退 `template_reply`，记录日志 |
| `need_human=True` 但 LLM 未加转人工提示 | 回退 `template_reply` |

### 代码示意

```python
def generate_reply(state):
    # 1. 先生成模板回复
    template_reply = _build_reply(state)

    # 2. 如果 LLM 润色未开启，直接返回模板
    if not os.getenv("LLM_ENABLE_REPLY_POLISH") == "true":
        return {"reply": template_reply, "logs": logs}

    # 3. 构建 payload
    payload = _build_llm_payload(state, template_reply)

    # 4. 调用 LLM
    try:
        result = llm_provider.generate_reply(payload)
        if "error" in result:
            return {"reply": template_reply, ...}
        # 5. Safety 检查
        check = safety.validate_llm_reply(result["reply"], state)
        if not check["safe"]:
            print(f"[llm] safety 拦截: {check['reason']}")
            return {"reply": template_reply, ...}
        # 6. 安全通过，使用 LLM 回复
        return {"reply": result["reply"], ...}
    except Exception as e:
        print(f"[llm] 调用失败: {e}")
        return {"reply": template_reply, ...}
```

---

## 八、Safety 检查设计

### 函数签名

```python
def validate_llm_reply(reply: str, state: dict) -> dict:
    """
    检查 LLM 回复是否安全。

    Returns:
        {"safe": True/False, "reason": "", "blocked_terms": []}
    """
```

### 拦截规则

| 危险词 | 拦截原因 |
|--------|---------|
| 已经退款 / 已退款成功 / 退款已完成 | LLM 不能承诺退款 |
| 已补发 / 已补偿 / 已赔偿 | LLM 不能承诺补偿 |
| 已取消订单 / 已修改地址 | LLM 不能操作订单 |
| 已为您处理完成 | 模糊承诺，不可追溯 |
| 已发货 / 已经发了 | 物流状态由 Tool 返回 |

### 特殊规则

```
如果 need_human=True:
  LLM 回复中必须包含 "人工" 或 "转人工"
  否则视为不安全，回退模板
```

---

## 九、接入位置设计

### 第一阶段：只接 generate_reply

```
当前流程（不变）：
  skill_result → generate_reply → 模板回复

LLM 开启后流程：
  skill_result → generate_reply
                    ↓
              生成 template_reply（原有逻辑不变）
                    ↓
              构建 payload（不含 API key）
                    ↓
              LLM Provider.generate_reply(payload)
                    ↓
              Safety 检查 → 通过 → LLM 回复
                           → 失败 → 回退 template_reply
```

### 不接的位置

```
❌ classify_intent  — 关键词 + 上下文已够用，不优先接入 LLM
❌ refund_policy   — Policy 必须代码控制
❌ escalation_policy — Policy 必须代码控制
❌ route_to_skill   — 路由必须代码控制
```

---

## 十、测试设计

新增 `tests/test_llm_provider.py`：

| # | 测试 | 断言 |
|---|------|------|
| 1 | mock_provider 返回 template_reply | `result["reply"] == template_reply` |
| 2 | provider_factory 默认返回 mock | `isinstance(provider, MockLLMProvider)` |
| 3 | 无 API key 时默认 mock，不崩溃 | 调用正常 |
| 4 | safety 拦截"已退款成功" | `safe=False` |
| 5 | safety 放行正常回复 | `safe=True` |
| 6 | need_human=True 但 LLM 无转人工提示 | `safe=False` |
| 7 | LLM 失败时 fallback 到 template_reply | 返回 `template_reply` |

---

## 十一、Phase 10.12 实现边界

### 允许修改

| 文件 | 操作 |
|------|------|
| `app/llm/__init__.py` | **新建** |
| `app/llm/base.py` | **新建** |
| `app/llm/mock_provider.py` | **新建** |
| `app/llm/deepseek_provider.py` | **新建**（骨架，不接真实 API） |
| `app/llm/provider_factory.py` | **新建** |
| `app/llm/safety.py` | **新建** |
| `app/nodes/generate_reply.py` | **小范围修改** — 增加 LLM 润色开关 |
| `.env.example` | **更新** — 增加 LLM 配置项 |
| `app/tests/test_llm_provider.py` | **新建** |
| `README.md` | 少量补充 |

### 不得修改

| 文件 | 原因 |
|------|------|
| `app/policies/` | 退款 / 转人工规则不变 |
| `app/graph.py` | 主流程不变 |
| `app/tools/` | 知识库工具不变 |
| `app/api/` | API 逻辑不变 |
| `app/web/` | UI 不变 |
| `app/skills/` | Skill 业务逻辑不变 |

---

## 十二、验收标准

| # | 验收项 | 验证方式 |
|---|--------|---------|
| 1 | 默认 mock provider，不调用真实 API | `LLM_PROVIDER=mock` 生效 |
| 2 | pytest 全部通过 | 运行测试 |
| 3 | 没有 API key 也能运行 | `.env` 空 key 时正常 |
| 4 | LLM 关闭时行为和 Phase 10.10 一致 | `LLM_ENABLE_REPLY_POLISH=false` |
| 5 | LLM 开启后只润色回复 | Safety 保证 |
| 6 | LLM 输出不安全时自动 fallback | 测试覆盖 |
| 7 | 退款 / 转人工 Policy 不被绕过 | 代码审查 |

---

> **下一阶段建议：** 进入 **Phase 10.12**，根据本文档实现 LLM Provider 层。
