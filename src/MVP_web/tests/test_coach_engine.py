"""
Coach Engine 单元测试
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCoachSSO:
    """教练 SSO 测试"""

    def test_coach_sso_token_generation(self):
        """测试 SSO token 生成"""
        from coach.coach_engine import coach_sso_token

        with patch.dict('os.environ', {'COACH_SSO_SECRET': 'test_secret'}):
            token = coach_sso_token("test_user")
            assert token is not None
            assert len(token) == 32

    def test_coach_sso_token_empty_secret(self):
        """测试空密钥时返回 None"""
        from coach.coach_engine import coach_sso_token

        with patch.dict('os.environ', {'COACH_SSO_SECRET': ''}):
            token = coach_sso_token("test_user")
            assert token is None

    def test_coach_sso_token_empty_username(self):
        """测试空用户名时返回 None"""
        from coach.coach_engine import coach_sso_token

        with patch.dict('os.environ', {'COACH_SSO_SECRET': 'test_secret'}):
            token = coach_sso_token("")
            assert token is None

    def test_verify_coach_sso_token_valid(self):
        """测试有效 token 验证"""
        from coach.coach_engine import coach_sso_token, verify_coach_sso_token

        with patch.dict('os.environ', {'COACH_SSO_SECRET': 'test_secret'}):
            token = coach_sso_token("test_user")
            result = verify_coach_sso_token("test_user", token)
            assert result is True

    def test_verify_coach_sso_token_invalid(self):
        """测试无效 token 验证"""
        from coach.coach_engine import verify_coach_sso_token

        with patch.dict('os.environ', {'COACH_SSO_SECRET': 'test_secret'}):
            result = verify_coach_sso_token("test_user", "invalid_token")
            assert result is False


class TestSafetyTriage:
    """安全分流测试"""

    def test_assess_risk_low(self):
        """测试低风险评估"""
        from coach.coach_engine import assess_risk

        result = assess_risk("孩子2岁了还不会说话")
        assert result["level"] == 1
        assert result["risk_type"] == "low"

    def test_assess_risk_high_parent_crisis(self):
        """测试家长危机信号检测"""
        from coach.coach_engine import assess_risk

        result = assess_risk("我真的撑不下去了，想带孩子一起走")
        assert result["level"] == 4
        assert result["risk_type"] == "emergency"

    def test_crisis_response_emergency(self):
        """测试紧急危机响应"""
        from coach.coach_engine import crisis_response

        response = crisis_response(4)
        assert "400-161-9995" in response
        assert "安全" in response or "重要" in response

    def test_crisis_response_high(self):
        """测试高度风险响应"""
        from coach.coach_engine import crisis_response

        response = crisis_response(3)
        assert len(response) > 0


class TestEmotionDetection:
    """情绪检测测试"""

    def test_detect_emotion_anxiety(self):
        """测试焦虑检测"""
        from coach.coach_engine import detect_emotion

        emotion, confidence = detect_emotion("我最近很焦虑，晚上睡不着")
        assert emotion is not None
        assert confidence > 0

    def test_detect_emotion_guilt(self):
        """测试愧疚检测"""
        from coach.coach_engine import detect_emotion

        emotion, confidence = detect_emotion("我觉得都是我的错")
        # 可能有愧疚相关检测
        assert isinstance(emotion, (str, type(None)))
        assert isinstance(confidence, int)

    def test_detect_emotion_negation(self):
        """测试否定处理"""
        from coach.coach_engine import detect_emotion, _count_keyword

        # "不焦虑" 应该不触发焦虑
        count = _count_keyword("我不焦虑", "焦虑")
        assert count == 0

    def test_detect_emotion_no_match(self):
        """测试无匹配"""
        from coach.coach_engine import detect_emotion

        emotion, confidence = detect_emotion("今天天气不错")
        assert emotion is None
        assert confidence == 0


class TestCoachResponse:
    """教练响应生成测试"""

    def test_generate_coach_response_safe(self):
        """测试安全输入的响应生成"""
        from coach.coach_engine import generate_coach_response_v2

        response = generate_coach_response_v2(
            "今天孩子表现不错",
            []
        )
        assert len(response) > 0

    def test_generate_coach_response_crisis(self):
        """测试危机输入的响应生成"""
        from coach.coach_engine import generate_coach_response_v2

        response = generate_coach_response_v2(
            "我撑不下去了",
            []
        )
        assert "400-161-9995" in response

    def test_generate_coach_response_with_history(self):
        """测试带历史的响应生成"""
        from coach.coach_engine import generate_coach_response_v2

        history = [
            {"role": "user", "content": "我最近很焦虑"},
            {"role": "assistant", "content": "能多说一些吗？"}
        ]
        response = generate_coach_response_v2("还是焦虑怎么办", history)
        assert len(response) > 0

    def test_detect_issue_type(self):
        """测试议题类型检测"""
        from coach.coach_engine import detect_issue_type

        issue_type = detect_issue_type("我和孩子的关系有问题")
        assert isinstance(issue_type, str)


class TestLLMCoach:
    """LLM 教练测试"""

    def test_llm_coach_reply_no_key(self):
        """测试无 API Key 时返回 None"""
        from coach.coach_engine import llm_coach_reply

        with patch.dict('os.environ', {
            'MINIMAX_API_KEY': '',
            'OPENAI_API_KEY': '',
            'ANTHROPIC_API_KEY': '',
            'DOUBAO_API_KEY': ''
        }):
            result = llm_coach_reply("测试输入", [])
            assert result is None

    def test_strip_reasoning(self):
        """测试推理内容剥离"""
        from coach.coach_engine import _strip_reasoning

        text = "<think>思考内容<|im_end|>\n\n这是实际回复"
        result = _strip_reasoning(text)
        assert "<think>" not in result
        assert "这是实际回复" in result

    def test_history_to_messages(self):
        """测试历史消息转换"""
        from coach.coach_engine import _history_to_messages

        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好吗？"}
        ]
        messages = _history_to_messages(history)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
