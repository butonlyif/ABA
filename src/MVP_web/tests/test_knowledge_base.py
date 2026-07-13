"""
KnowledgeBase 单元测试
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestKnowledgeBase:
    """KnowledgeBase 测试"""

    def setup_method(self):
        """每个测试前初始化临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_kb_path = Path(self.temp_dir) / "knowledge"
        self.temp_kb_path.mkdir()
        self.temp_db_path = Path(self.temp_dir) / "chromadb"

    def teardown_method(self):
        """清理临时文件"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_directories(self):
        """测试初始化创建目录"""
        from ai.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )

        assert self.temp_db_path.exists()

    def test_chunk_id_generation(self):
        """测试 chunk ID 生成"""
        from ai.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )

        chunk = {"source": "test.md", "content": "测试内容"}
        chunk_id = kb._chunk_id(chunk, 0)

        assert isinstance(chunk_id, str)
        assert len(chunk_id) == 32  # SHA256 前32位

    def test_chunk_id_deterministic(self):
        """测试 chunk ID 生成是确定性的"""
        from ai.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )

        chunk = {"source": "test.md", "content": "测试内容"}
        id1 = kb._chunk_id(chunk, 0)
        id2 = kb._chunk_id(chunk, 0)

        assert id1 == id2

    def test_chunk_id_different_for_different_content(self):
        """测试不同内容生成不同 ID"""
        from ai.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )

        chunk1 = {"source": "test.md", "content": "内容1"}
        chunk2 = {"source": "test.md", "content": "内容2"}

        assert kb._chunk_id(chunk1, 0) != kb._chunk_id(chunk2, 0)

    def test_embedding_text_format(self):
        """测试 embedding 文本格式"""
        from ai.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )

        chunk = {
            "title": "测试标题",
            "source": "test.md",
            "content": "这是测试内容"
        }

        text = kb._embedding_text(chunk)

        assert "测试标题" in text
        assert "test.md" in text
        assert "这是测试内容" in text

    def test_load_documents_empty_directory(self):
        """测试加载空目录"""
        from ai.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )

        count = kb.load_documents()
        assert count == 0
        assert kb.get_document_count() == 0

    def test_load_documents_with_files(self):
        """测试加载文档"""
        from ai.knowledge_base import KnowledgeBase

        # 创建测试文档
        test_file = self.temp_kb_path / "test.md"
        test_file.write_text("# 测试文档\n\n这是测试内容。", encoding="utf-8")

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )

        count = kb.load_documents()
        assert count == 1
        assert kb.get_document_count() == 1

    def test_create_chunks(self):
        """测试文档分块"""
        from ai.knowledge_base import KnowledgeBase

        # 创建包含多个段落的文档
        content = "\n\n".join([f"段落{i}" for i in range(10)])
        test_file = self.temp_kb_path / "test.md"
        test_file.write_text(content, encoding="utf-8")

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )

        kb.load_documents()
        assert kb.get_chunk_count() > 0

    def test_format_context_empty(self):
        """测试格式化空结果"""
        from ai.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )

        result = kb.format_context([])
        assert result == ""

    def test_format_context_with_results(self):
        """测试格式化搜索结果"""
        from ai.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )

        results = [
            {"title": "文档1", "content": "内容1"},
            {"title": "文档2", "content": "内容2"}
        ]

        formatted = kb.format_context(results)

        assert "相关知识库内容" in formatted
        assert "文档1" in formatted
        assert "内容1" in formatted

    def test_search_without_collection(self):
        """测试无 collection 时的搜索"""
        from ai.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )
        # 不加载文档，直接搜索

        results = kb.search("测试查询")
        assert results == []

    def test_get_recommended_documents_empty(self):
        """测试空干预目标的推荐"""
        from ai.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )

        results = kb.get_recommended_documents("")
        assert results == []

    def test_get_all_documents_info(self):
        """测试获取所有文档信息"""
        from ai.knowledge_base import KnowledgeBase

        # 创建测试文档
        test_file = self.temp_kb_path / "test.md"
        test_file.write_text("# 测试", encoding="utf-8")

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )

        kb.load_documents()
        info = kb.get_all_documents_info()

        assert len(info) == 1
        assert "title" in info[0]
        assert "source" in info[0]

    def test_get_semantic_rerank_candidates_empty(self):
        """测试空知识库的候选"""
        from ai.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(
            knowledge_path=str(self.temp_kb_path),
            vector_db_path=str(self.temp_db_path)
        )

        candidates = kb.get_semantic_rerank_candidates()
        assert candidates == []
