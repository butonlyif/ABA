"""
Coach Content 单元测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCoachContent:
    """教练内容数据测试"""

    def test_kb_articles_exist(self):
        """测试知识库文章存在"""
        from coach.coach_content import KB_ARTICLES

        assert isinstance(KB_ARTICLES, dict)
        assert len(KB_ARTICLES) > 0

    def test_kb_articles_structure(self):
        """测试知识库文章结构"""
        from coach.coach_content import KB_ARTICLES

        for key, article in KB_ARTICLES.items():
            assert "title" in article
            assert "category" in article
            assert "content" in article

    def test_emotion_keywords_exist(self):
        """测试情绪关键词存在"""
        from coach.coach_content import EMOTION_KEYWORDS

        assert isinstance(EMOTION_KEYWORDS, dict)
        assert len(EMOTION_KEYWORDS) > 0

    def test_emotion_keywords_structure(self):
        """测试情绪关键词结构"""
        from coach.coach_content import EMOTION_KEYWORDS

        for emotion, keywords in EMOTION_KEYWORDS.items():
            assert isinstance(keywords, list)
            assert len(keywords) > 0
            assert all(isinstance(kw, str) for kw in keywords)

    def test_emotion_coach_strategies_exist(self):
        """测试情绪教练策略存在"""
        from coach.coach_content import EMOTION_COACH_STRATEGIES

        assert isinstance(EMOTION_COACH_STRATEGIES, dict)

    def test_emotion_coach_strategies_structure(self):
        """测试情绪教练策略结构"""
        from coach.coach_content import EMOTION_COACH_STRATEGIES

        for emotion, strategy in EMOTION_COACH_STRATEGIES.items():
            assert "opening" in strategy
            assert "follow_ups" in strategy
            assert isinstance(strategy["follow_ups"], list)

    def test_issue_type_keywords_exist(self):
        """测试议题类型关键词存在"""
        from coach.coach_content import ISSUE_TYPE_KEYWORDS

        assert isinstance(ISSUE_TYPE_KEYWORDS, dict)

    def test_growth_stages_exist(self):
        """测试成长阶段存在"""
        from coach.coach_content import GROWTH_STAGES

        assert isinstance(GROWTH_STAGES, dict)
        assert len(GROWTH_STAGES) > 0

    def test_coach_styles_exist(self):
        """测试教练风格存在"""
        from coach.coach_content import COACH_STYLES

        assert isinstance(COACH_STYLES, dict)
