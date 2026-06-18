"""
knowledge_qa_skill.py — 知识库问答技能。

使用 RAG Provider 检索非结构化文档（售后政策、保养说明、FAQ 等），
基于 retrieved_chunks 返回 evidence。
"""

from app.knowledge.rag_provider import RagProvider

# 全局单例 RagProvider（首次调用时自动构建）
_rag = RagProvider()
_rag_initialized = False


def _ensure_rag():
    global _rag_initialized
    if not _rag_initialized:
        _rag.build_index()
        _rag_initialized = True


def run_knowledge_qa_skill(state: dict) -> dict:
    """
    执行知识库问答，基于 RAG 检索返回 evidence。

    读取字段：user_message, conversation_history
    写入字段：skill_result
    """
    text = state.get("user_message", "") or ""

    _ensure_rag()
    result = _rag.retrieve(text, top_k=3)

    if not result.get("matched") or not result.get("retrieved_chunks"):
        return {
            "skill_result": {
                "action": "knowledge_qa",
                "source": "rag",
                "success": False,
                "matched": False,
                "retrieved_chunks": [],
                "evidence": [],
                "message": "这部分资料暂时没有检索到，我建议转人工确认。",
            }
        }

    chunks = result["retrieved_chunks"]
    evidence = [
        {"source_file": c["source_file"], "score": c["score"]}
        for c in chunks
    ]

    # 根据证据组织回复
    message = _build_answer_from_chunks(chunks)

    return {
        "skill_result": {
            "action": "knowledge_qa",
            "source": "rag",
            "success": True,
            "matched": True,
            "retrieved_chunks": chunks,
            "evidence": evidence,
            "message": message,
        }
    }


def _build_answer_from_chunks(chunks: list) -> str:
    """从 retrieved_chunks 中组织回复文本。"""
    top = chunks[0]
    source = top["source_file"]
    text = top["text"]

    lines = [text]
    lines.append(f"\n（来源：{source}）")

    if len(chunks) > 1:
        lines.append("\n\n更多相关信息：")
        for c in chunks[1:]:
            lines.append(f"- {c['text'][:80]}…（{c['source_file']}）")

    return "\n".join(lines)
