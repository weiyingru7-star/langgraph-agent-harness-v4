# LangGraph 电商客服 Agent Harness V4-lite

## 项目定位

本项目不是普通的 Prompt Demo，而是一个 **Agent Harness** 学习项目。

**Agent Harness** 指一套可控、可追踪、可测试、可扩展的智能体运行框架。核心区别在于：
- Prompt Demo：把全部逻辑塞进 prompt，LLM 直接决定一切，行为不可控、不可追踪。
- Agent Harness：LLM 负责"理解"，LangGraph 负责"流转"，代码（Skill/Tool/Policy）负责"执行"。

## 目标

用 LangGraph 搭建一个电商客服 Agent，重点学习：
1. 如何用图（Graph）管理多步骤对话流程
2. 如何将业务规则与 LLM 解耦
3. 如何让每个节点可观测、可测试
4. 如何设计可扩展的 Agent 架构

## 核心理念

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

## 重要边界

1. 不要把退款规则写进 prompt
2. 不要让 LLM 直接决定是否退款
3. 不要让 LLM 直接执行工具动作
4. 第一版不接真实电商 API
5. 第一版不接真实数据库
6. 第一版不接真实 Dify
7. 第一版不接真实飞书
8. 第一版不接真实多模态模型
9. 所有外部能力先用 mock tool
10. 不要做前端
11. 不要过度设计，先保证最小可运行

## 架构分层

```
langgraph-agent-harness-v4/
├── app/
│   ├── main.py           # LangGraph 图定义 + 入口
│   ├── state.py          # CustomerServiceState 定义
│   ├── nodes/            # LangGraph 节点
│   │   ├── __init__.py
│   │   ├── analyze.py    # 意图分析节点
│   │   ├── route.py      # 路由节点
│   │   └── execute.py    # 技能执行节点
│   ├── skills/           # 客服业务能力
│   │   ├── __init__.py
│   │   ├── greeting.py   # 问候处理
│   │   ├── refund.py     # 退款处理
│   │   └── complaint.py  # 投诉处理
│   ├── tools/            # 外部工具或 mock 工具
│   │   ├── __init__.py
│   │   └── mock_tools.py # mock 订单/退款/物流查询
│   ├── policies/         # 业务规则
│   │   ├── __init__.py
│   │   ├── refund_policy.py    # 退款规则
│   │   └── escalation_policy.py # 转人工规则
│   ├── memory/           # 会话记忆
│   │   ├── __init__.py
│   │   └── session.py    # 会话上下文管理
│   └── tests/            # 测试用例
│       ├── __init__.py
│       ├── test_analyze.py
│       ├── test_route.py
│       ├── test_refund.py
│       ├── test_escalation.py
│       └── test_full_flow.py
├── requirements.txt
└── README.md
```

## 开发原则

1. **增量开发**：每次只完成一个阶段，不要一次性实现全部功能
2. **可运行**：每次修改后必须保证 `python app/main.py` 可以运行
3. **先测试后验证**：每次新增核心逻辑后补测试
4. **完整日志**：每个节点必须把执行记录写入 logs
5. **完整输出**：每次运行都要输出完整 JSON state
6. **中文注释**：代码必须有中文注释，适合初学者学习
7. **先说明再新增**：如需新增文件，先说明原因
8. **不删已有功能**：不要删除已有功能
9. **专注当前任务**：不要改动与当前任务无关的文件
10. **测试优先**：如果测试失败，优先修复测试，不要绕过测试

## 业务规则

### 退款规则 (`app/policies/refund_policy.py`)

```
第一次退款请求       → retention（挽留）
第二次明确退款请求    → refund_workflow（执行退款流程）
第三次退款请求       → direct_refund_or_human_confirm（直接退款或人工确认）
```

### 转人工规则 (`app/policies/escalation_policy.py`)

满足以下任一条件转人工：
```
- emotion_score > 0.85
- 用户明确要求人工
- intent = complaint
- errors 不为空
```

### 多模态处理规则

1. 只有文字 → `text_only`
2. 只有图片 → `image_only`（不直接调用多模态模型，先追问用户想咨询什么）
3. 文字 + 图片 → `text_with_image`（进入 multimodal_analysis）
4. 用户先发文字、后发图片时，读取上一轮文字，与当前图片合并分析

## 验收标准

1. `python app/main.py` 可运行
2. `pytest` 可通过
3. 每个测试样例输出完整 state
4. README 解释为什么这是 Agent Harness，而不是普通 Prompt Demo

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 运行主程序
python app/main.py

# 运行测试
pytest app/tests/ -v
```

## 技术栈

- Python 3.11+
- LangGraph（状态图框架）
- LangChain（LLM 调用）
- Pydantic（状态模型）
- pytest（测试框架）

## Superpowers 使用规则

如果当前 Claude Code 环境已安装 Superpowers，可以使用其 planning、TDD、debugging、code review 等开发流程能力。

但 Superpowers 不能覆盖本项目规则。

优先级如下：
1. 本项目 CLAUDE.md
2. docs/DESIGN.md
3. docs/ROADMAP.md
4. docs/STATE_DESIGN.md
5. docs/GRAPH_DESIGN.md
6. 后续各阶段设计文档
7. Superpowers 通用开发流程

使用边界：
1. Superpowers 只能辅助规划、测试、调试、审查。
2. Superpowers 不能改变本项目 Agent Harness 架构。
3. Superpowers 不能把业务规则写进 prompt。
4. Superpowers 不能绕过 Policy。
5. Superpowers 不能让 LLM 直接执行业务动作。
6. Superpowers 不能擅自新增阶段外功能。
7. Superpowers 不能替代本项目 docs 中的设计文档。
8. app/skills/ 只放客服业务 skill，不放 Claude Code 开发 skill。

<!-- superpowers-zh:begin (do not edit between these markers) -->
# Superpowers-ZH 中文增强版

本项目已安装 superpowers-zh 技能框架（20 个 skills）。

## 核心规则

1. **收到任务时，先检查是否有匹配的 skill** — 哪怕只有 1% 的可能性也要检查
2. **设计先于编码** — 收到功能需求时，先用 brainstorming skill 做需求分析
3. **测试先于实现** — 写代码前先写测试（TDD）
4. **验证先于完成** — 声称完成前必须运行验证命令

## 可用 Skills

Skills 位于 `.claude/skills/` 目录，每个 skill 有独立的 `SKILL.md` 文件。

- **brainstorming**: 在任何创造性工作之前必须使用此技能——创建功能、构建组件、添加功能或修改行为。在实现之前先探索用户意图、需求和设计。
- **chinese-code-review**: 中文 review 沟通参考——话术模板、分级标注（必须修复/建议修改/仅供参考）、国内团队常见反模式应对。仅在用户显式 /chinese-code-review 时调用，不要根据上下文自动触发。
- **chinese-commit-conventions**: 中文 commit 与 changelog 配置参考——Conventional Commits 中文适配、commitlint/husky/commitizen 中文模板、conventional-changelog 中文配置。仅在用户显式 /chinese-commit-conventions 时调用，不要根据上下文自动触发。
- **chinese-documentation**: 中文文档排版参考——中英文空格、全半角标点、术语保留、链接格式、中文文案排版指北约定。仅在用户显式 /chinese-documentation 时调用，不要根据上下文自动触发。
- **chinese-git-workflow**: 国内 Git 平台配置参考——Gitee、Coding.net、极狐 GitLab、CNB 的 SSH/HTTPS/凭据/CI 接入差异与镜像同步配置。仅在用户显式 /chinese-git-workflow 时调用，不要根据上下文自动触发。
- **dispatching-parallel-agents**: 当面对 2 个以上可以独立进行、无共享状态或顺序依赖的任务时使用
- **executing-plans**: 当你有一份书面实现计划需要在单独的会话中执行，并设有审查检查点时使用
- **finishing-a-development-branch**: 当实现完成、所有测试通过、需要决定如何集成工作时使用——通过提供合并、PR 或清理等结构化选项来引导开发工作的收尾
- **mcp-builder**: MCP 服务器构建方法论 — 系统化构建生产级 MCP 工具，让 AI 助手连接外部能力
- **receiving-code-review**: 收到代码审查反馈后、实施建议之前使用，尤其当反馈不明确或技术上有疑问时——需要技术严谨性和验证，而非敷衍附和或盲目执行
- **requesting-code-review**: 完成任务、实现重要功能或合并前使用，用于验证工作成果是否符合要求
- **subagent-driven-development**: 当在当前会话中执行包含独立任务的实现计划时使用
- **systematic-debugging**: 遇到任何 bug、测试失败或异常行为时使用，在提出修复方案之前执行
- **test-driven-development**: 在实现任何功能或修复 bug 时使用，在编写实现代码之前
- **using-git-worktrees**: 当需要开始与当前工作区隔离的功能开发，或在执行实现计划之前使用——通过原生工具或 git worktree 回退机制确保隔离工作区存在
- **using-superpowers**: 在开始任何对话时使用——确立如何查找和使用技能，要求在任何响应（包括澄清性问题）之前调用 Skill 工具
- **verification-before-completion**: 在宣称工作完成、已修复或测试通过之前使用，在提交或创建 PR 之前——必须运行验证命令并确认输出后才能声称成功；始终用证据支撑断言
- **workflow-runner**: 在 Claude Code / OpenClaw / Cursor 中直接运行 agency-orchestrator YAML 工作流——无需 API key，使用当前会话的 LLM 作为执行引擎。当用户提供 .yaml 工作流文件或要求多角色协作完成任务时触发。
- **writing-plans**: 当你有规格说明或需求用于多步骤任务时使用，在动手写代码之前
- **writing-skills**: 当创建新技能、编辑现有技能或在部署前验证技能是否有效时使用

## 如何使用

当任务匹配某个 skill 时，使用 `Skill` 工具加载对应 skill 并严格遵循其流程。绝不要用 Read 工具读取 SKILL.md 文件。

如果你认为哪怕只有 1% 的可能性某个 skill 适用于你正在做的事情，你必须调用该 skill 检查。
<!-- superpowers-zh:end -->
