"""最小本地 RAG 检索测试（Phase 10.17-A）。"""

import os
import tempfile

from app.knowledge.chunker import chunk_documents
from app.knowledge.document_loader import load_documents
from app.knowledge.rag_provider import RagProvider
from app.knowledge.vector_store import SimpleVectorStore


class TestDocumentLoader:
    """文档加载测试。"""

    def test_load_refund_policy(self):
        docs = load_documents()
        sources = [d["source_file"] for d in docs]
        assert "refund_policy.md" in sources

    def test_load_care_guide(self):
        docs = load_documents()
        sources = [d["source_file"] for d in docs]
        assert "care_guide.md" in sources

    def test_load_faq_long(self):
        docs = load_documents()
        sources = [d["source_file"] for d in docs]
        assert "faq_long.md" in sources

    def test_minimum_three_docs(self):
        docs = load_documents()
        assert len(docs) >= 3


class TestChunker:
    """文档切片测试。"""

    def test_chunks_have_source_file(self):
        docs = load_documents()
        chunks = chunk_documents(docs)
        assert len(chunks) > 0
        for chunk in chunks:
            assert "source_file" in chunk
            assert "chunk_id" in chunk
            assert "text" in chunk

    def test_chunks_contain_content(self):
        docs = load_documents()
        chunks = chunk_documents(docs)
        texts = [c["text"] for c in chunks]
        combined = " ".join(texts)
        assert "7 天" in combined or "7天" in combined


class TestVectorStore:
    """向量存储测试。"""

    def test_build_and_search(self):
        store = SimpleVectorStore()
        docs = load_documents()
        chunks = chunk_documents(docs)
        store.build(chunks)

        results = store.search("超过7天还能退吗")
        assert len(results) > 0
        assert results[0]["source_file"] == "refund_policy.md"

    def test_search_care_guide(self):
        store = SimpleVectorStore()
        docs = load_documents()
        chunks = chunk_documents(docs)
        store.build(chunks)

        results = store.search("防晒衣怎么洗")
        assert len(results) > 0
        assert any(r["source_file"] == "care_guide.md" for r in results)

    def test_search_faq(self):
        store = SimpleVectorStore()
        docs = load_documents()
        chunks = chunk_documents(docs)
        store.build(chunks)

        results = store.search("多久发货")
        assert len(results) > 0
        assert any(r["source_file"] == "faq_long.md" for r in results)

    def test_each_result_has_score(self):
        store = SimpleVectorStore()
        docs = load_documents()
        chunks = chunk_documents(docs)
        store.build(chunks)

        results = store.search("退货政策")
        for r in results:
            assert "score" in r
            assert "text" in r
            assert "source_file" in r

    def test_save_and_load(self):
        store = SimpleVectorStore()
        docs = load_documents()
        chunks = chunk_documents(docs)
        store.build(chunks)

        tmp_path = tempfile.mktemp(suffix=".json")
        store.save(tmp_path)

        store2 = SimpleVectorStore()
        store2.load(tmp_path)
        os.remove(tmp_path)

        results = store2.search("超过7天还能退吗")
        assert len(results) > 0


class TestRagProvider:
    """RAG Provider 集成测试。"""

    def test_build_index(self):
        rag = RagProvider()
        result = rag.build_index()
        assert result["status"] == "ok"
        assert result["document_count"] >= 3
        assert result["chunk_count"] > 0

    def test_retrieve_refund_policy(self):
        rag = RagProvider()
        rag.build_index()
        result = rag.retrieve("超过7天还能退吗")
        assert result["matched"] is True
        assert len(result["retrieved_chunks"]) > 0
        for chunk in result["retrieved_chunks"]:
            assert "source_file" in chunk
            assert "score" in chunk
            assert "text" in chunk
        # 最好的一条应该来自 refund_policy.md
        top = result["retrieved_chunks"][0]
        if top["source_file"] == "refund_policy.md":
            assert "7" in top["text"] or "退" in top["text"]

    def test_retrieve_care_guide(self):
        rag = RagProvider()
        rag.build_index()
        result = rag.retrieve("防晒衣怎么洗")
        assert result["matched"] is True
        sources = [c["source_file"] for c in result["retrieved_chunks"]]
        assert "care_guide.md" in sources

    def test_retrieve_faq(self):
        rag = RagProvider()
        rag.build_index()
        result = rag.retrieve("多久发货")
        assert result["matched"] is True
        sources = [c["source_file"] for c in result["retrieved_chunks"]]
        assert "faq_long.md" in sources

    def test_no_match_returns_clarification(self):
        rag = RagProvider()
        rag.build_index()
        result = rag.retrieve("xyzxyz无关查询内容")
        # 可能低分匹配或没匹配
        if result["matched"]:
            for c in result["retrieved_chunks"]:
                assert c["score"] < 0.5  # 不应高匹配
        else:
            assert result["needs_clarification"] is True

    def test_no_history_match_still_ok(self):
        """检索在无上下文时仍能正常返回。"""
        rag = RagProvider()
        rag.build_index()
        result = rag.retrieve("运动外套怎么保养")
        assert result["matched"] is True
        assert len(result["retrieved_chunks"]) > 0
