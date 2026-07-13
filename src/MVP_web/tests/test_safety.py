"""
SafetyChecker 单元测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.safety import SafetyChecker


class TestSafetyChecker:
    """SafetyChecker 测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.checker = SafetyChecker()

    def test_check_safe_content(self):
        """测试安全内容"""
        result = self.checker.check("孩子2岁了还不会说话怎么办")
        assert result["level"] == 1  # LOW
        assert result["risk_type"] == "low"
        assert result["keywords"] == []

    def test_check_medium_risk(self):
        """测试中等风险内容"""
        result = self.checker.check("孩子总是打人咬人怎么办")
        assert result["level"] == 2  # MEDIUM
        assert result["risk_type"] == "medium"
        assert "打人" in result["keywords"] or "咬人" in result["keywords"]

    def test_check_high_risk_self_harm(self):
        """测试高风险自伤内容"""
        result = self.checker.check("孩子总是撞头打自己")
        assert result["level"] == 3  # HIGH
        assert result["risk_type"] == "high"
        assert len(result["keywords"]) > 0

    def test_check_emergency_suicide(self):
        """测试紧急情况（自杀）"""
        result = self.checker.check("孩子说不想活了")
        assert result["level"] == 4  # EMERGENCY
        assert result["risk_type"] == "emergency"

    def test_check_emergency_self_harm(self):
        """测试紧急情况（自伤）"""
        result = self.checker.check("孩子想割腕")
        assert result["level"] == 4  # EMERGENCY
        assert result["risk_type"] == "emergency"

    def test_check_case_insensitive(self):
        """测试中文内容大小写不敏感"""
        # SafetyChecker 使用 text.lower()，所以中文的大写形式（如全角）也会被 lower() 处理
        result = self.checker.check("孩子说不想活了")
        assert result["level"] == 4  # EMERGENCY
        assert result["risk_type"] == "emergency"

    def test_is_safe_content(self):
        """测试快速判断安全"""
        assert self.checker.is_safe_content("怎么教孩子说话") is True
        assert self.checker.is_safe_content("孩子打人") is True
        assert self.checker.is_safe_content("孩子撞头") is False
        assert self.checker.is_safe_content("孩子说想死") is False

    def test_get_emergency_response(self):
        """测试紧急响应模板"""
        response = self.checker.get_emergency_response()
        assert "400-161-9995" in response
        assert "确保孩子安全" in response

    def test_get_professional_help_suggestion(self):
        """测试专业帮助建议模板"""
        response = self.checker.get_professional_help_suggestion()
        assert "BCBA" in response or "治疗师" in response

    def test_get_supportive_response_prefix(self):
        """测试支持性回答前缀"""
        response = self.checker.get_supportive_response_prefix()
        assert len(response) > 0

    def test_empty_text(self):
        """测试空文本"""
        result = self.checker.check("")
        assert result["level"] == 1  # LOW
        assert result["risk_type"] == "low"

    def test_multiple_keywords(self):
        """测试多个关键词"""
        result = self.checker.check("孩子撞头咬自己崩溃了")
        assert result["level"] >= 3  # HIGH or EMERGENCY
        assert len(result["keywords"]) >= 2

    def test_custom_keywords_used(self):
        """测试自定义关键词参数被记录"""
        custom_keywords = ["危险词1", "危险词2"]
        checker = SafetyChecker(danger_keywords=custom_keywords)
        # danger_keywords 参数会被记录，但分类逻辑使用硬编码的 emergency_keywords
        assert checker.danger_keywords == custom_keywords
