"""
====================================
ABA智能助手 - 安全检查模块
====================================

负责检测用户输入中的安全问题
确保AI回复的安全性
"""

from typing import Dict, List, Optional
import re

try:
    from core.config import (
        DANGER_KEYWORDS,
        SAFETY_LEVEL_EMERGENCY,
        SAFETY_LEVEL_HIGH,
        SAFETY_LEVEL_MEDIUM,
        SAFETY_LEVEL_LOW
    )
except ImportError:
    # 默认配置
    DANGER_KEYWORDS = [
        "自杀", "自伤", "想死", "不想活了",
        "割腕", "跳楼", "吃药", "上吊",
        "杀人", "弄死", "打死",
        "撞头", "打自己", "咬自己",
        "不吃饭", "不喝水", "绝食"
    ]
    SAFETY_LEVEL_EMERGENCY = 4
    SAFETY_LEVEL_HIGH = 3
    SAFETY_LEVEL_MEDIUM = 2
    SAFETY_LEVEL_LOW = 1


class SafetyChecker:
    """安全检查器"""
    
    def __init__(
        self,
        danger_keywords: Optional[List[str]] = None
    ):
        """
        初始化安全检查器
        
        Args:
            danger_keywords: 危险关键词列表
        """
        self.danger_keywords = danger_keywords or DANGER_KEYWORDS
        
        # 分类危险关键词
        self.emergency_keywords = [
            # 自杀/自伤相关
            "自杀", "自伤", "想死", "不想活了", "活着没意思",
            "割腕", "跳楼", "吃药", "上吊", "不想活了",
            
            # 极端行为
            "不吃饭", "不喝水", "绝食", "拒绝吃喝",
        ]
        
        self.high_risk_keywords = [
            # 攻击相关
            "杀人", "弄死", "打死", "伤害",
            
            # 严重自伤
            "撞头", "打自己", "咬自己", "自伤",
            
            # 心理危机
            "崩溃", "绝望", "无助", "抑郁",
        ]
        
        self.medium_risk_keywords = [
            # 行为问题
            "打人", "咬人", "攻击", "暴力",
            
            # 情绪问题
            "焦虑", "抑郁", "情绪", "脾气",
            
            # 发展担忧
            "发育", "智力", "能力", "落后",
        ]
    
    def check(self, text: str) -> Dict:
        """
        检查文本的安全性
        
        Args:
            text: 待检查的文本
            
        Returns:
            检查结果字典
            {
                "level": 1-4,  # 安全级别
                "keywords": [],  # 匹配的关键词
                "risk_type": "",  # 风险类型
                "message": ""    # 建议信息
            }
        """
        text_lower = text.lower()
        
        # 检查紧急风险
        emergency_matches = self._check_keywords(text_lower, self.emergency_keywords)
        if emergency_matches:
            return {
                "level": SAFETY_LEVEL_EMERGENCY,
                "keywords": emergency_matches,
                "risk_type": "emergency",
                "message": "检测到紧急信号，需要立即关注",
                "action": "provide_emergency_info"
            }
        
        # 检查高风险
        high_matches = self._check_keywords(text_lower, self.high_risk_keywords)
        if high_matches:
            return {
                "level": SAFETY_LEVEL_HIGH,
                "keywords": high_matches,
                "risk_type": "high",
                "message": "检测到高风险信号，建议专业介入",
                "action": "suggest_professional_help"
            }
        
        # 检查中等风险
        medium_matches = self._check_keywords(text_lower, self.medium_risk_keywords)
        if medium_matches:
            return {
                "level": SAFETY_LEVEL_MEDIUM,
                "keywords": medium_matches,
                "risk_type": "medium",
                "message": "检测到需要关注的问题",
                "action": "provide_supportive_response"
            }
        
        # 低风险/安全
        return {
            "level": SAFETY_LEVEL_LOW,
            "keywords": [],
            "risk_type": "low",
            "message": "内容安全",
            "action": "normal_response"
        }
    
    def _check_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """检查是否包含关键词"""
        matches = []
        for keyword in keywords:
            if keyword in text:
                matches.append(keyword)
        return matches
    
    def get_emergency_response(self) -> str:
        """获取紧急情况响应模板"""
        return """
🚨 **【重要提示】**

您提到的情况需要高度重视。

**立即行动：**
1. 确保孩子安全，不让孩子独处
2. 移除环境中可能的危险物品
3. 保持冷静，陪在孩子身边

**尽快寻求专业帮助：**
• 联系孩子的治疗师或督导
• 就诊儿童精神科
• 拨打心理援助热线：400-161-9995

**请记住：**
✓ 您已经在寻求帮助，这很重要
✓ 您不是一个人
✓ 这些困难是可以克服的
✓ 专业的帮助是有效的
"""
    
    def get_professional_help_suggestion(self) -> str:
        """获取建议专业介入的响应模板"""
        return """
⚠️ **【温馨提示】**

您提到的情况建议咨询专业人员的帮助。

**可以考虑：**
• 孩子的ABA治疗师或BCBA督导
• 儿童精神科医生
• 发育行为科医生
• 心理咨询师

**准备就诊时：**
• 记录孩子具体的行为表现
• 记录行为发生的时间、频率、场景
• 记录可能的触发因素
• 带上孩子的评估报告（如有）

**日常可以做的：**
✓ 继续使用有效的干预策略
✓ 保持作息规律
✓ 记录进步和挑战
✓ 寻求家人支持

如果情况紧急或加重，请立即就医！
"""
    
    def get_supportive_response_prefix(self) -> str:
        """获取支持性回答的前缀"""
        return """
💙 **【理解你的担忧】**

我能理解这让你感到担心。每个家长在面对这些挑战时都会感到压力。

"""
    
    def is_safe_content(self, text: str) -> bool:
        """
        快速判断内容是否安全
        
        Args:
            text: 待检查的文本
            
        Returns:
            True表示安全，False表示需要关注
        """
        result = self.check(text)
        return result["level"] < SAFETY_LEVEL_HIGH


# ====================================
# 紧急资源信息
# ====================================

class EmergencyResources:
    """紧急资源信息"""
    
    CHINA_RESOURCES = {
        "心理援助热线": "400-161-9995",
        "全国心理援助热线": "010-82951332",
        "北京心理危机研究与干预中心": "010-82951150",
        "儿童希望基金会": "400-000-9131"
    }
    
    @classmethod
    def get_all_resources(cls) -> str:
        """获取所有紧急资源"""
        resources = "\n".join([
            f"• **{name}**：{phone}"
            for name, phone in cls.CHINA_RESOURCES.items()
        ])
        
        return f"""
**【紧急联系资源】**

{resources}

如果情况紧急，请拨打120急救或前往最近的医院急诊。
"""
    
    @classmethod
    def get_emergency_info(cls) -> str:
        """获取紧急情况信息"""
        return """
**【紧急情况处理】**

1. **确保安全**
   - 移开危险物品
   - 不让孩子独处
   - 保持冷静

2. **立即求助**
   - 拨打120急救
   - 联系最近的医院急诊
   - 通知家人朋友协助

3. **专业支持**
   - 儿童精神科急诊
   - 心理危机干预热线
"""


# ====================================
# 测试代码
# ====================================

if __name__ == "__main__":
    print("=" * 50)
    print("安全检查器测试")
    print("=" * 50)
    
    checker = SafetyChecker()
    
    test_texts = [
        "孩子最近总说要死",
        "孩子总是撞头打自己",
        "孩子发脾气时打人怎么办",
        "怎么教孩子说话",
        "孩子2岁了还不会说话"
    ]
    
    for text in test_texts:
        result = checker.check(text)
        print(f"\n文本: {text}")
        print(f"级别: {result['level']} - {result['risk_type']}")
        print(f"关键词: {result['keywords']}")
        print(f"建议: {result['message']}")
        print("-" * 30)
