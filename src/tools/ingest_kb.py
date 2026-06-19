"""
知识库索引构建脚本
==================
把 docs/知识库/ 下的文档（md/txt/pdf/docx）切块并写入向量库（ChromaDB）。
这是「让 AI 问答真正用上书」的关键一步：app 启动时只『打开』已建好的索引，
不会自己重建；新增书本/资料后，跑一次本脚本即可增量入库（按内容哈希去重）。

用法：
    python3 src/tools/ingest_kb.py            # 用默认知识库目录
    python3 src/tools/ingest_kb.py <自定义目录>

embedding 后端：
    - 配置了 EMBEDDING_API_KEY/OPENAI_API_KEY → 远程 API；
    - 否则自动用本地 MiniLM（chromadb 内置，首次运行会下载 ~80MB 模型，需联网一次，之后离线可用）。

退出码：0 = 成功且索引非空；1 = 失败或索引为空。
"""

import os
import sys

_THIS = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.dirname(_THIS)
_ROOT = os.path.dirname(_SRC)
_MVP = os.path.join(_SRC, "MVP_web")
sys.path.insert(0, _MVP)

from ai.knowledge_base import KnowledgeBase  # noqa: E402
from core.config import KNOWLEDGE_BASE_PATH, VECTOR_DB_PATH  # noqa: E402


def main():
    kb_path = sys.argv[1] if len(sys.argv) > 1 else KNOWLEDGE_BASE_PATH
    print("=" * 50)
    print("知识库索引构建")
    print("-" * 50)
    print(f"知识库目录: {kb_path}")
    print(f"向量库目录: {VECTOR_DB_PATH}")

    if not os.path.isdir(kb_path):
        print(f"❌ 知识库目录不存在: {kb_path}")
        sys.exit(1)

    kb = KnowledgeBase(knowledge_path=kb_path, vector_db_path=VECTOR_DB_PATH)
    print(f"Collection: {kb.collection_name}（{kb.embedding_mode}）")

    if not kb.embedding_enabled:
        print("❌ embedding 不可用，无法建索引。请检查 EMBEDDING_API_KEY 或本地 onnxruntime 安装。")
        sys.exit(1)

    n_docs = kb.load_documents()
    print(f"加载文档: {n_docs} 个，切块: {kb.get_chunk_count()} 块")

    # 校验索引非空
    try:
        count = kb.collection.count()
    except Exception:
        count = -1
    print(f"向量库当前条目数: {count}")
    print("-" * 50)

    if count and count > 0:
        # 抽样检索自检
        sample = kb.search("什么是正强化", top_k=3)
        if sample:
            print(f"✅ 自检检索命中 {len(sample)} 条，最高分 {round(sample[0]['score'], 3)}")
        print("✅ 索引构建完成")
        sys.exit(0)

    print("❌ 索引为空，构建失败")
    sys.exit(1)


if __name__ == "__main__":
    main()
