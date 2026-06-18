# LangGraph 电商客服 Agent Harness V4-lite

## 这是什么？

本项目是一个 **Agent Harness 学习项目**，使用 LangGraph 搭建电商客服智能体框架。

## 为什么这是 Agent Harness，而不是普通 Prompt Demo？

### Prompt Demo 的做法

```
用户输入 → LLM（prompt 中写了所有规则）→ 回复
```

所有逻辑塞进 prompt，LLM 决定一切：
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

关键差异：

| 维度 | Prompt Demo | Agent Harness |
|------|-------------|---------------|
| **规则位置** | 写在 prompt 里 | 写在 Policy 代码里 |
| **决策方式** | LLM 直接决策 | Policy 代码判断 |
| **动作执行** | LLM 决定是否调用工具 | Graph 路由到指定 Skill |
| **可观测性** | LLM 输出即全部 | 每个节点有独立日志 |
| **可测试性** | 只能端到端测试 | 每个节点/策略可单独测试 |
| **可控性** | 低，LLM 可能"自由发挥" | 高，代码控制关键路径 |
| **可维护性** | 改需求 = 改 prompt | 改需求 = 改对应模块 |

### 一句话总结

> **LLM 负责理解，不直接执行业务动作。业务决策交给代码，流程控制交给 LangGraph。**

## 架构分层

```
app/
├── main.py              # LangGraph 图定义 + 入口
├── graph.py             # 图构建
├── state/               # 状态定义 (CustomerServiceState)
│   └── customer_state.py
├── nodes/               # LangGraph 节点（流程中的每一步）
│   ├── parse_input.py       # 输入解析
│   ├── decide_modality.py   # 模态判断
│   ├── analyze_text.py      # 文本分析
│   ├── analyze_multimodal.py # 多模态分析
│   ├── classify_intent.py   # 意图分类
│   ├── classify_emotion.py  # 情绪分析
│   ├── classify_stage.py    # 对话阶段分类
│   ├── route_to_skill.py    # 路由到技能
│   ├── generate_reply.py    # 回复生成
│   ├── escalation_check.py  # 转人工检查
│   └── save_log.py          # 日志保存
├── skills/              # 客服业务能力
│   ├── product_qa_skill.py      # 商品问答
│   ├── recommendation_skill.py  # 商品推荐
│   ├── logistics_skill.py       # 物流查询
│   ├── refund_skill.py          # 退款处理
│   ├── exchange_skill.py        # 换货处理
│   ├── complaint_skill.py       # 投诉处理
│   └── human_skill.py           # 转人工
├── tools/               # 外部工具/mock
│   ├── mock_order_tool.py
│   ├── mock_product_tool.py
│   └── mock_multimodal_tool.py
├── policies/            # 业务规则
│   ├── refund_policy.py
│   └── escalation_policy.py
├── memory/              # 会话记忆
│   └── conversation_memory.py
└── tests/               # 测试用例
    ├── test_text_only.py
    ├── test_image_only.py
    ├── test_text_with_image.py
    ├── test_refund_flow.py
    └── test_human_transfer.py
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行主程序
python app/main.py

# 运行测试
pytest app/tests/ -v
```

## 核心原则

1. **LLM 只负责理解** — 不直接执行业务动作
2. **Policy 负责判断** — 业务规则写在代码里
3. **Skill 负责执行** — 每个技能独立封装
4. **Graph 负责流转** — LangGraph 控制流程
5. **每个节点可测试** — 每个模块都有对应测试
6. **每一步都有日志** — 完整追踪状态变化
