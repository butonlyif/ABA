"""
Config 模块单元测试
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConfig:
    """配置模块测试"""

    def test_base_dir_exists(self):
        """测试 BASE_DIR 存在"""
        from core.config import BASE_DIR
        assert BASE_DIR.exists()

    def test_ai_models_defined(self):
        """测试 AI 模型配置存在"""
        from core.config import AI_MODELS, DEFAULT_MODEL

        assert isinstance(AI_MODELS, dict)
        assert len(AI_MODELS) > 0
        assert DEFAULT_MODEL in AI_MODELS

    def test_model_structure(self):
        """测试模型配置结构"""
        from core.config import AI_MODELS

        for model_id, config in AI_MODELS.items():
            assert "name" in config
            assert "model" in config
            assert "api_key_env" in config

    def test_safety_levels_ordered(self):
        """测试安全级别顺序"""
        from core.config import (
            SAFETY_LEVEL_EMERGENCY,
            SAFETY_LEVEL_HIGH,
            SAFETY_LEVEL_MEDIUM,
            SAFETY_LEVEL_LOW
        )

        assert SAFETY_LEVEL_EMERGENCY > SAFETY_LEVEL_HIGH
        assert SAFETY_LEVEL_HIGH > SAFETY_LEVEL_MEDIUM
        assert SAFETY_LEVEL_MEDIUM > SAFETY_LEVEL_LOW

    def test_danger_keywords_not_empty(self):
        """测试危险关键词列表非空"""
        from core.config import DANGER_KEYWORDS

        assert isinstance(DANGER_KEYWORDS, list)
        assert len(DANGER_KEYWORDS) > 0

    def test_retrieval_config(self):
        """测试检索配置"""
        from core.config import (
            RETRIEVAL_TOP_K,
            RETRIEVAL_CANDIDATE_K,
            RETRIEVAL_SCORE_THRESHOLD
        )

        assert RETRIEVAL_TOP_K > 0
        assert RETRIEVAL_CANDIDATE_K > RETRIEVAL_TOP_K
        assert 0 <= RETRIEVAL_SCORE_THRESHOLD <= 1

    def test_collection_names_different(self):
        """测试 API 和本地 collection 名称不同"""
        from core.config import COLLECTION_NAME, COLLECTION_NAME_LOCAL

        assert COLLECTION_NAME != COLLECTION_NAME_LOCAL

    def test_system_prompt_not_empty(self):
        """测试系统提示词存在"""
        from core.config import SYSTEM_PROMPT

        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 100

    def test_default_user_structure(self):
        """测试默认用户结构"""
        from core.config import DEFAULT_USER

        required_fields = [
            "child_name", "child_age", "child_diagnosis",
            "intervention_goals", "parent_name", "notes"
        ]
        for field in required_fields:
            assert field in DEFAULT_USER

    def test_app_title_defined(self):
        """测试应用标题定义"""
        from core.config import APP_TITLE

        assert isinstance(APP_TITLE, str)
        assert len(APP_TITLE) > 0
