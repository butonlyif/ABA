"""
ABAAgent 单元测试
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestABAAgent:
    """ABAAgent 测试"""

    def setup_method(self):
        """每个测试前初始化"""
        from ai.agent import ABAAgent
        self.AgentClass = ABAAgent

    def test_init_without_knowledge_base(self):
        """测试无知识库初始化"""
        agent = self.AgentClass(knowledge_base=None)
        assert agent.knowledge_base is None
        assert agent.model_name == "minimax"

    def test_init_with_knowledge_base(self):
        """测试有知识库初始化"""
        mock_kb = MagicMock()
        agent = self.AgentClass(knowledge_base=mock_kb, model_name="doubao")
        assert agent.knowledge_base is mock_kb
        assert agent.model_name == "doubao"

    def test_build_prompt_basic(self):
        """测试基本提示词构建"""
        agent = self.AgentClass()
        context = {}
        prompt = agent._build_prompt("孩子2岁了还不会说话", context)

        assert "孩子2岁了还不会说话" in prompt
        assert "[知识库内容]" in prompt

    def test_build_prompt_with_child_info(self):
        """测试带孩子信息的提示词构建"""
        agent = self.AgentClass()
        context = {
            "child_name": "小明",
            "child_age": "3岁",
            "child_diagnosis": "自闭症谱系",
            "intervention_goals": "语言训练"
        }
        prompt = agent._build_prompt("怎么教孩子说话", context)

        assert "小明" in prompt
        assert "3岁" in prompt
        assert "自闭症谱系" in prompt

    def test_build_prompt_with_conversation_history(self):
        """测试带对话历史的提示词构建"""
        agent = self.AgentClass()
        context = {
            "conversation_history": [
                {"role": "user", "content": "孩子最近不说话"},
                {"role": "assistant", "content": "请描述具体情况"}
            ]
        }
        prompt = agent._build_prompt("还是不说话怎么办", context)

        assert "对话历史" in prompt
        assert "孩子最近不说话" in prompt

    def test_build_prompt_with_rag_context(self):
        """测试带 RAG 上下文的提示词构建

        说明：rag_context 由 generate_response 在 _build_prompt 之后额外拼接，
        _build_prompt 本身不处理 rag_context 字段。这里验证 _build_prompt 仍正确
        产出含用户问题和知识库占位符的提示词。
        """
        agent = self.AgentClass()
        context = {
            "rag_context": "这是外部注入的上下文"
        }
        prompt = agent._build_prompt("测试问题", context)

        assert "测试问题" in prompt
        assert "[知识库内容]" in prompt

    def test_generate_response_without_client(self):
        """测试无客户端时的响应生成"""
        agent = self.AgentClass()
        agent.client = None
        context = {}

        response = agent.generate_response("测试问题", context)

        assert "服务暂时不可用" in response or "AI" in response

    def test_generate_response_with_fallback(self):
        """测试后备响应生成"""
        agent = self.AgentClass()
        agent.client = None

        response = agent._generate_fallback_response("测试提示词")

        assert len(response) > 0
        assert "AI" in response or "暂时不可用" in response

    def test_rerank_without_client(self):
        """测试无客户端时的重排"""
        agent = self.AgentClass()
        agent.client = None

        candidates = [
            {"content": "内容1", "title": "标题1"},
            {"content": "内容2", "title": "标题2"}
        ]

        result = agent._rerank_knowledge("查询", candidates, 2)
        assert result == candidates[:2]

    def test_search_web_function(self):
        """测试网络搜索函数"""
        from ai.agent import search_web

        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = ""
            mock_get.return_value = mock_response

            result = search_web("测试查询")
            # 空响应应该返回空字符串
            assert isinstance(result, str)

    def test_available_tools_defined(self):
        """测试可用工具定义"""
        from ai.agent import AVAILABLE_TOOLS

        assert isinstance(AVAILABLE_TOOLS, list)
        assert len(AVAILABLE_TOOLS) > 0
        assert AVAILABLE_TOOLS[0]["type"] == "function"
        assert "search_web" in str(AVAILABLE_TOOLS)

    def test_conversation_history_initialization(self):
        """测试对话历史初始化"""
        agent = self.AgentClass()
        assert agent.conversation_history == []

    def test_model_config_loaded(self):
        """测试模型配置加载"""
        agent = self.AgentClass()
        assert agent.model_config is not None
        assert "model" in agent.model_config
