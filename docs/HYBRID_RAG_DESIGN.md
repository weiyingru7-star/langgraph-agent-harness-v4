# 混合知识库设计 — HYBRID_RAG_DESIGN

> **Phase 10.16 · 设计文档**
> 目标：设计结构化字段 + RAG 非结构化文档的混合知识库方案。

---

## 一、为什么不是全部改成 RAG

### 结构化字段 vs RAG 的适用场景

| 维度 | 结构化查询 (products.json) | RAG 向量检索 |
|------|---------------------------|-------------|
| 尺码、价格、颜色 | ✅ 精确，直接从字段读取 | ❌ 可能检索出错片断 |
| 材质、成分 | ✅ 精确 | ❌ LLM 可能编造 |
| 售后政策 | ❌ 不适合结构化存储 | ✅ 适合文档检索 |
| 安装说明 | ❌ 字段存不下 | ✅ 适合文档检索 |
| 比较两个商品 | ❌ 需要推理 | ✅ LLM 适合对比 |
| 退货流程 | ❌ 流程化内容 | ✅ 适合文档检索 |

### 全部用 RAG 的风险

```
❌ 用户问"运动外套多少钱"
   RAG 检索到"轻量运动外套 249-399 元"的概率不高
   如果同时 chunks 里有"防晒衣 129-199 元"，可能回答错误

✅ 结构化查询
   直接读取 products.json → "轻量运动外套 249-399 元"
   100% 准确
```

**结论：结构化字段 > RAG，RAG 只做结构化做不了的事。**

---

## 二、混合知识库架构

```
用户问题
    ↓
classify_intent + Product QA Resolver
    ↓
query_type 识别
    ↓
Knowledge Router
   ├── size / price / color / material / stock
   │   └── structured_provider → products.json
   │
   ├── refund_policy / installation / maintenance / long_faq / comparison
   │   └── rag_provider → vector_store → retrieved_chunks → LLM
   │
   ├── structured 缺失
   │   └── fallback → rag_provider
   │
   └── 两者都无结果
       └── needs_clarification / human_handoff
```

---

## 三、Knowledge Router 设计

### 路由规则

```python
def route_query(query_type: str) -> str:
    """根据 query_type 决定走哪个 Provider。"""
    if query_type in ("size", "price", "color", "material", "stock", "sku"):
        return "structured"
    if query_type in ("refund_policy", "after_sale", "installation",
                       "maintenance", "comparison", "long_faq", "general_doc"):
        return "rag"
    return "hybrid"  # 先试 structured，缺失再走 RAG
```

### Provider 统一接口

```python
class BaseKnowledgeProvider(ABC):
    @abstractmethod
    def retrieve(self, query: str, context: dict) -> dict:
        """
        返回：
        {
            "source": "structured" | "rag" | "hybrid",
            "matched": bool,
            "answer_data": dict | None,
            "retrieved_chunks": [
                {"text": "...", "source_file": "...", "score": 0.95}
            ],
            "needs_clarification": bool,
            "reason": str
        }
        """
```

---

## 四、数据目录设计

建议保持与现有结构一致：

```
data/
├── products.json          # 结构化商品（不变）
├── faq.json               # 短 FAQ（不变）
├── refund_policy.md       # 退款政策（RAG 原始文档）
├── rag/                   # ★ 新增 RAG 目录
│   ├── raw/               # 原始文档
│   │   ├── refund_policy.md
│   │   ├── after_sale_policy.md
│   │   ├── shipping_policy.md
│   │   ├── product_guides/
│   │   │   ├── 防晒衣使用说明.md
│   │   │   └── 运动外套保养指南.md
│   └── chroma_db/         # Chroma 本地向量库文件
```

---

## 五、第一版 RAG 技术选型

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|------|
| **Dify 知识库** | 上手快、免开发、带 UI | 看不到代码实现、依赖外部服务 | ⭐⭐ |
| **Chroma / FAISS 本地** | 代码完整、适合作品集、本地可跑 | 需要处理 embedding 和索引 | ⭐⭐⭐ |
| **Milvus / pgvector** | 企业级 | 部署重、当前阶段不需要 | ⭐ |

**推荐：Chroma 或 FAISS 本地向量库。**

理由：
- 作品集展示自研 RAG，面试官能看到完整的检索→排序→生成链路
- 本地可跑，不依赖外部服务
- embedding 可以用 sentence-transformers 或在线的 text-embedding-3-small

---

## 六、RAG 流程设计

### 文档导入流程

```
knowledge/raw/*.md
    ↓
document_loader.py
    ↓ 解析文本、分割段落
chunker.py
    ↓ 按 chunk_size=512, overlap=64 切片
chunks.jsonl
    ↓
embedding_provider.py
    ↓ 调用 embedding 模型
vector_store.py
    ↓ 写入 Chroma/FAISS
vector_store 索引
```

### 查询流程

```
user_message + conversation_history
    ↓
query_rewrite（可选）
    ↓
embedding → vector_store.similarity_search(query, top_k=5)
    ↓
retrieved_chunks + source_file
    ↓
LLM 基于 chunks 生成回答
    ↓
safety 检查
    ↓
返回 answer + evidence
```

### Chunk 格式

```json
{
  "chunk_id": "refund_policy_001",
  "source_file": "data/rag/raw/refund_policy.md",
  "text": "首次退款请求，优先安抚用户情绪，确认问题原因。",
  "metadata": {
    "page": 1,
    "section": "首次退款",
    "intent": ["refund_request"]
  }
}
```

---

## 七、与 DeepSeek 的关系

DeepSeek 在 RAG 中有两个角色：

### 角色 1：Reply Polisher（已有）

```
template_reply → DeepSeek 润色 → safety → 回复
```

### 角色 2：RAG Answer Generator（新增）

```
retrieved_chunks + query
    ↓
DeepSeek 基于 chunks 生成回答
    ↓
必须引用证据（source_file）
    ↓
safety 检查
    ↓
返回 answer + evidence
```

### 不允许 LLM 做的事

```
❌ 无 chunks 时编造答案
❌ 回答 refund_policy 时绕过 refund_policy.py
❌ 回答商品字段时编造不存在的规格
❌ LLM 自行决定退款
```

---

## 八、与 Product QA Resolver 的关系

```
Product QA Resolver 输出：
    matched_product, query_type, needs_clarification

Hybrid Router 根据 query_type 决定：
    1. query_type = size/price/color/material
       → structured_provider（继续用 products.json）
       → 不走 RAG

    2. query_type = 其他，但 structured 字段缺失
       → fallback RAG

    3. query_type = refund_policy/installation/long_faq
       → 直接走 RAG
```

**Product QA Resolver 保持不变。Hybrid Router 是新增的调度层。**

---

## 九、测试设计

| # | 测试 | 验证 |
|---|------|------|
| 1 | 尺码问题优先走 structured | structured_provider 命中，不走 RAG |
| 2 | 价格问题优先走 structured | 同上 |
| 3 | 售后政策问题走 RAG | rag_provider 命中，返回 source_file |
| 4 | 安装说明问题走 RAG | 同上 |
| 5 | structured 缺失时可 fallback RAG | router 返回 hybrid |
| 6 | RAG 无结果时不编造 | needs_clarification 或转人工 |
| 7 | RAG 结果必须带 source_file | 响应中包含证据来源 |
| 8 | 退款请求仍然走 policy | Policy 不被 RAG 覆盖 |
| 9 | pytest 全部通过 | — |

---

## 十、Phase 10.17 实现建议

### Phase 10.17-A：最小本地 RAG

```
允许新增：
  knowledge/
  app/knowledge/
  data/rag/

实现：
  1. document_loader.py — 读取 Markdown
  2. chunker.py — 简单切片
  3. embedding_provider.py — 调用在线 API 或本地模型
  4. vector_store.py — Chroma 或 FAISS 存/查
  5. rag_provider.py — retrieve + LLM answer
```

### Phase 10.17-B：Next.js 前端展示证据

在 Agent 分析面板中增加：
- knowledge_source
- evidence_chunks
- source_file 链接

### 暂不做

```
❌ 全部商品改 RAG
❌ Milvus
❌ Dify 接入
❌ PDF/Word 解析（第一版只支持 Markdown）
❌ query_rewrite（第一版直接用原始 query）
❌ 多轮 RAG
```

---

## 十一、禁止事项

| 禁止 | 原因 |
|------|------|
| RAG 决定退款 | Policy 控制 |
| RAG 修改 policy_decision | Policy 控制 |
| LLM 无检索结果时编造 | 必须明确"资料不足" |
| 把所有商品字段改成 RAG | 结构化更准确 |
| 引入 Milvus | 太重 |
| 破坏现有 160 测试 | — |
| 修改 app/graph.py | 主流程不变 |
| 修改 app/policies/ | 业务规则不变 |

---

> **下一阶段建议：** 进入 **Phase 10.17-A**，实现最小本地 RAG（Markdown 文档切片 + Chroma/FAISS 向量检索）。
