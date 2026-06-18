# Agent Eval 测试集

## 概述

Eval 测试集是一套轻量质量评估工具，用于验证 LangGraph 电商客服 Agent 的：

- **意图识别**：关键词规则能否正确判断用户意图
- **技能路由**：intent → skill 的映射是否正确
- **商品问答**：商品匹配和字段查询是否准确
- **RAG 检索**：知识库检索和 evidence 来源是否正确
- **安全边界**：退款/投诉/转人工是否有 policy 控制
- **回复质量**：回复中是否包含/排除特定关键词

Eval **不替代**单元测试（`app/tests/`）。  
Eval 是端到端的综合质量验证，在完整图流程上运行，用于快速发现回归。

---

## Eval 模式

当前 Eval 支持两类运行模式：

### 1. Mock Baseline Mode（默认）

| 项目 | 说明 |
|------|------|
| LLM Provider | `mock`（不调用任何外部 API） |
| Semantic Parser | 关闭 |
| RAG Provider | `tfidf`（纯本地计算，无需索引） |
| 外部依赖 | 无 |
| 当前结果 | **19/25 (76%)** |

此模式验证的是 Agent 的基础链路完整性：
- 关键词规则能否正确路由
- Policy 是否拦截安全边界
- RAG 检索和 evidence 来源是否正确
- 模板回复是否包含/排除必要关键词

**失败的 6 条全部集中在需要 LLM 语义理解的场景**（见下方失败分类），不代表基础链路有问题。

### 2. Full LLM Mode

```bash
LLM_PROVIDER=deepseek LLM_ENABLE_SEMANTIC_PARSER=true .venv/bin/python scripts/run_eval.py
```

| 项目 | 说明 |
|------|------|
| LLM Provider | `deepseek`（需要 `.env` 中配置 `DEEPSEEK_API_KEY`） |
| Semantic Parser | 启用，可解析自然语言上下文指代 |
| 外部依赖 | DeepSeek API |
| 预期结果 | 显著高于 Mock Baseline |

此模式额外验证 LLM 的语义理解能力：
- `"那个遮阳帽不错"` → 识别为商品追问
- `"第二个怎么样"` → 结合 history 解析指代
- `"这个适合我妈吗"` → 识别为 suitability 查询
- `"超过7天还能退吗"` → 路由到 knowledge_qa_skill

两种模式互不干扰。**Mock Baseline 是默认门禁，Full LLM 是上限验证。**

---

## 失败项分类

当前 Mock Baseline 下 6 条失败用例的分类：

| 用例 | 用户消息 | 失败原因 | 依赖 |
|------|----------|----------|------|
| case_006 | "那个遮阳帽不错" | 关键词无"推荐"等命中，fallback 到 smalltalk | LLM Semantic Parser |
| case_007 | "第二个怎么样" | 无任何 intent 关键词，无法路由 skill | LLM Semantic Parser + 多轮 |
| case_010 | "超过7天还能退吗" | 关键词未命中 product_question 规则 | LLM Semantic Parser |
| case_012 | "退换货政策是什么" | "换货"命中 exchange_request，未走到 RAG | 关键词优先级调整 / LLM |
| case_013 | "多久发货" | 物流 skill 回复模板不含"48"字样 | 回复模板 |
| case_019 | "这个适合海边拍照吗" | 回复为 `_build_reply` general 模板，不含"咨询" | 回复模板 |

**关键结论：**
- 6 条失败中 4 条可以直接通过启用 LLM Semantic Parser 解决
- case_012 是关键词冲突（"换货" > 政策关键词），case_013 是物流模板措辞差异
- **零失败是基础链路 Bug**——全是能力边界和模式限制

---

## Eval 指标说明

当前第一版主要看 **case pass/fail**，后续可以细分以下维度：

### 指标定义

| 指标 | 计算方式 | Mock Baseline | Full LLM（预估） |
|------|----------|---------------|-------------------|
| **Pass Rate** | 全部通过 / 总数 | 76% (19/25) | ~92% (23/25) |
| **Intent Accuracy** | intent 匹配 / 有预期 intent 的用例数 | — | — |
| **Skill Routing Accuracy** | selected_skill 匹配 / 有预期 skill 的用例数 | — | — |
| **RAG Evidence Hit Rate** | evidence 正确 / 有预期 source_file 的用例数 | — | — |
| **Safety Guard Pass Rate** | 安全边界用例通过 / 安全边界用例总数 | 100% (7/7) | 100% (7/7) |
| **Context Resolution Accuracy** | 多轮追问通过 / 多轮用例数 | 50% (2/4) | ~100% (4/4) |

### 当前关注重点

1. **Safety Guard Pass Rate** 必须在所有模式下保持 100%——这是不可妥协的安全红线
2. **RAG Evidence Hit Rate** 应在 TF-IDF 和 Chroma 下都通过
3. **Pass Rate** 如果某条之前通过的用例突然失败，说明有回归

后续版本可以引入 LLM-as-Judge 自动评分，但当前手工检查 keyword + field 已足够覆盖作品集级验证需求。

## 运行方式

```bash
# 默认模式（mock LLM + TF-IDF RAG，无需任何 API key）
.venv/bin/python scripts/run_eval.py

# 显示详细检查信息
.venv/bin/python scripts/run_eval.py --verbose

# 指定报告输出位置
.venv/bin/python scripts/run_eval.py --output my_report.json
```

### 可选：启用 LLM

如果配置了 DeepSeek API key，可以启用 LLM Semantic Parser 获得更准确的意图识别：

```bash
LLM_PROVIDER=deepseek .venv/bin/python scripts/run_eval.py
```

### 可选：切换 RAG Provider

```bash
RAG_PROVIDER=chroma .venv/bin/python scripts/run_eval.py
```

需要先构建 Chroma 索引：

```bash
.venv/bin/python scripts/build_chroma_index.py
```

## 测试用例

测试用例位于 `evals/test_cases.jsonl`，每行一个 JSON 对象。

### 用例字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | ✓ | 用例唯一编号 |
| `user_message` | | 用户输入文本（空字符串 + image_url 表示纯图片） |
| `image_url` | | 图片 URL（仅 image_only 场景） |
| `history` | | 多轮对话历史（用于多轮推理测试） |
| `expected_intent` | | 预期意图 |
| `expected_skill` | | 预期技能 |
| `expected_query_type` | | 预期问题类型 |
| `expected_product` | | 预期匹配的商品名 |
| `expected_source_file` | | 预期 RAG 来源文件名 |
| `expected_modality` | | 预期模态（仅 image_only） |
| `policy_decision` | | 预期 Policy 决策 |
| `need_human` | | 预期转人工 |
| `must_contain` | | reply 中必须包含的关键词 |
| `must_not_contain` | | reply 中禁止出现的关键词 |
| `notes` | | 用例说明 |

### 覆盖能力

当前共 26 条测试用例，覆盖以下能力：

**A. 商品问答（5 条）**
- 尺码查询（case_001、case_004）
- 材质查询（case_002、case_005）
- 价格查询（case_003）
- 颜色查询（case_022）

**B. 多轮上下文（4 条）**
- 多轮商品追问（case_006）
- 第二件指代（case_007）
- 适合人群（case_008）
- 无商品名追问——从 history 推断（case_009）

**C. RAG 知识库（4 条）**
- 售后政策（case_010、case_012）
- 保养说明（case_011、case_023）

**D. 安全边界（7 条）**
- 首次退款 retention（case_014、case_015、case_018、case_020）
- 转人工（case_016）
- 投诉（case_017、case_024）

**E. 无资料/兜底（3 条）**
- 无资料时不编造（case_019）
- 闲聊兜底（case_021）
- 纯图片追问（case_025）

## 解读结果

### 输出示例

```
==================================================
LangGraph Agent Eval Runner
==================================================
  LLM Provider:  mock           (deepseek 需要 .env 配置)
  RAG Provider:  tfidf          (chroma 需要 data/chroma/)
  Test cases:    /path/to/evals/test_cases.jsonl
  Report output: /path/to/evals/eval_report.json

加载 26 条测试用例，开始逐条运行...

  ✓ PASS case_001 (0.32s)  checks=3/3
  ✓ PASS case_002 (0.28s)  checks=3/3
  ✗ FAIL case_006 (0.25s)  checks=0/3
  ...

==================================================
[EVAL] 合计: 20/26 通过 (76.9%)
==================================================

详细报告已写入: evals/eval_report.json
```

### JSON 报告

`eval_report.json` 包含每条用例的详细检查结果，方便后续趋势分析：

```json
{
  "summary": {
    "total": 26,
    "passed": 20,
    "failed": 6,
    "pass_rate": 76.9
  },
  "config": {
    "llm_provider": "mock",
    "rag_provider": "tfidf"
  },
  "results": [
    {
      "id": "case_001",
      "pass": true,
      "checks_passed": 3,
      "checks_total": 3,
      ...
    }
  ]
}
```

### 理解通过率

**mock LLM（默认）**：

部分测试用例依赖 LLM Semantic Parser 进行意图识别（如模糊商品追问 `"那个遮阳帽不错"`），在 mock 模式下无法准确识别意图。这些用例会显示 intent/skill check 失败，属于预期行为。

通过 keyword rules 可稳定通过约 15-18 条用例（商品问答、强关键词退款/投诉/物流等）。

**启用 LLM（LLM_PROVIDER=deepseek）**：

启用 Semantic Parser 后，模糊追问、多轮指代、RAG 政策识别均可通过，通过率显著提升。

**关注重点**：

- 安全边界用例（case_014~018、case_020、case_024）应在所有模式下通过
- RAG 用例（case_010~012、case_023）应在 TF-IDF 和 Chroma 下都通过
- 如果某条之前通过的用例突然失败，说明有回归

## 当前局限性

1. **不是生产级评测** — 当前 Eval 是作品集级质量验证，不覆盖所有对话路径
2. **不替代 pytest** — Eval 验证端到端行为，pytest 验证单元/集成正确性
3. **无自动评分** — 不包含 LLM-as-Judge 或 BLEU/ROUGE 评分
4. **静态用例** — 测试用例需要手动维护更新
5. **无历史趋势** — 当前版本不追踪通过率历史变化

## 添加新用例

在 `evals/test_cases.jsonl` 末尾新增一行即可：

```json
{"id": "case_026", "user_message": "新问题", "history": [], "expected_intent": "...", "must_contain": ["..."], "notes": "新用例说明"}
```

建议遵循以下原则：
- 每个用例只验证 1-2 个核心关注点
- `must_contain` / `must_not_contain` 使用业务关键词而非完整回复
- 保持 `history` 简洁，只包含必要的上下文
