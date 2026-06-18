"""
build_chroma_index.py — 构建 Chroma 向量索引。

从 knowledge/raw 读取文档，切 chunk，生成 embedding，写入 Chroma。

用法：
    .venv/bin/python scripts/build_chroma_index.py

环境变量：
    RAG_PROVIDER=chroma（可选，仅用于日志）
    EMBEDDING_MODEL（可选，默认 sentence-transformers/all-MiniLM-L6-v2）
"""

import os
import sys

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.knowledge.chroma_provider import ChromaProvider


def main():
    print("=" * 60)
    print("Chroma 索引构建工具")
    print("=" * 60)

    provider = ChromaProvider()
    result = provider.build_index()

    if result.get("status") == "ok":
        print(f"\n✅ 构建成功！")
        print(f"   文档数: {result['document_count']}")
        print(f"   Chunks: {result['chunk_count']}")
        print(f"   Embedding model: {result['embedding_model']}")
        print(f"   持久化路径: {result['persist_dir']}")
    else:
        print(f"\n❌ 构建失败: {result.get('reason', '未知错误')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
