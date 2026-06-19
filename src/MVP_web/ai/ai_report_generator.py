"""
====================================
ABA智能助手 - AI报告生成模块
====================================

集成真实AI模型生成个性化报告：
- MiniMax / OpenAI / 豆包 等LLM支持
- 对话数据分析
- 智能建议生成
- 个性化报告撰写
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()


class AIReportGenerator:
    """AI智能报告生成器"""

    def __init__(self, llm_provider: str = "minimax"):
        self.llm_provider = llm_provider
        self.llm_client = None
        self._init_llm_client()

    def _init_llm_client(self):
        """初始化LLM客户端"""
        if self.llm_provider == "minimax":
            try:
                from minimax import MiniMax
                api_key = os.getenv("MINIMAX_API_KEY")
                if api_key:
                    self.llm_client = MiniMax(api_key=api_key)
            except ImportError:
                print("⚠️ MiniMax SDK未安装")

        elif self.llm_provider == "openai":
            try:
                import openai
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self.llm_client = openai.OpenAI(api_key=api_key)
            except ImportError:
                print("⚠️ OpenAI SDK未安装")

        elif self.llm_provider == "zhipu":
            try:
                from zhipuai import ZhipuAI
                api_key = os.getenv("ZHIPU_API_KEY")
                if api_key:
                    self.llm_client = ZhipuAI(api_key=api_key)
            except ImportError:
                print("⚠️ 智谱AI SDK未安装")

    def generate_report_with_ai(
        self,
        child_info: Dict,
        progress_data: Dict,
        conversation_data: Dict
    ) -> str:
        """使用AI生成个性化报告"""

        if not self.llm_client:
            return self._generate_fallback_report(child_info, progress_data, conversation_data)

        prompt = self._build_report_prompt(child_info, progress_data, conversation_data)

        try:
            response = self._call_llm(prompt)
            return response
        except Exception as e:
            print(f"AI生成失败: {e}")
            return self._generate_fallback_report(child_info, progress_data, conversation_data)

    def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        if self.llm_provider == "minimax":
            response = self.llm_client.chat.completions.create(
                model="abab6-chat",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content

        elif self.llm_provider == "openai":
            response = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content

        elif self.llm_provider == "zhipu":
            response = self.llm_client.chat.completions.create(
                model="glm-4",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content

        raise ValueError(f"未知的LLM提供商: {self.llm_provider}")

    def _build_report_prompt(
        self,
        child_info: Dict,
        progress_data: Dict,
        conversation_data: Dict
    ) -> str:
        """构建报告生成提示词"""

        prompt = f"""
# ABA智能助手 - 阶段性报告生成

## 孩子基本信息
- 姓名: {child_info.get('name', '未知')}
- 年龄: {child_info.get('birth_date', '未知')}
- 诊断: {child_info.get('diagnosis', '未知')}
- 干预目标: {child_info.get('intervention_goals', '未设置')}

## 数据统计

### 对话统计
- 总对话轮次: {conversation_data.get('total', 0)}
- 家长提问数: {conversation_data.get('user_messages', 0)}
- AI回答数: {conversation_data.get('assistant_messages', 0)}

### 进展记录统计
- 总记录数: {progress_data.get('total_logs', 0)}
- 类别分布: {json.dumps(progress_data.get('by_category', {}), ensure_ascii=False, indent=2)}

### 家长关注话题
{json.dumps(progress_data.get('top_concerns', []), ensure_ascii=False, indent=2)}

### 进展趋势
- 趋势: {progress_data.get('trend', '数据不足')}
- 家长参与度: {progress_data.get('engagement_level', '中等')}

## 最近进展记录
{json.dumps(progress_data.get('recent_logs', [])[:10], ensure_ascii=False, indent=2)}

## 报告要求

请生成一份专业的ABA阶段性报告，包含：

1. **报告摘要** (2-3句话概括整体情况)
2. **数据分析**
   - 对话互动分析
   - 进展记录分析
   - 家长关注点分析
3. **专业建议** (3-5条针对性建议)
4. **下周期目标** (2-3个具体目标)
5. **温馨提醒**

要求：
- 语言专业但易懂，适合家长阅读
- 突出孩子的进步和亮点
- 建议要具体可操作
- 总字数800-1200字
- 使用中文
- 格式清晰，有层级标题
"""

        return prompt

    def _generate_fallback_report(
        self,
        child_info: Dict,
        progress_data: Dict,
        conversation_data: Dict
    ) -> str:
        """生成基础报告（当AI不可用时）"""

        total_logs = progress_data.get('total_logs', 0)
        conv_total = conversation_data.get('total', 0)
        trend = progress_data.get('trend', '稳定')
        engagement = progress_data.get('engagement_level', '中等')
        categories = progress_data.get('by_category', {})
        top_concerns = progress_data.get('top_concerns', [])

        trend_text = {
            "improving": "📈 呈进步趋势",
            "declining": "📉 需要关注",
            "stable": "➡️ 保持稳定",
            "insufficient_data": "➖ 数据不足"
        }.get(trend, "➖ 数据不足")

        engagement_text = {
            "high": "高度参与",
            "medium": "中等参与",
            "low": "参与较少"
        }.get(engagement, "中等")

        main_concern = top_concerns[0]['concern'] if top_concerns else "整体表现"

        report = f"""
# {child_info.get('name', '孩子')} - 阶段性报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 📋 报告摘要

{child_info.get('name', '您的孩子')}在干预期间整体{trend_text}，家长{engagement_text}。
{top_concerns[0]['concern'] if top_concerns else '各领域'}方面表现{'值得关注' if trend == 'declining' else '良好'}。

---

## 📊 数据分析

### 对话互动统计

| 指标 | 数值 |
|------|------|
| 总对话轮次 | {conv_total} |
| 家长提问数 | {conversation_data.get('user_messages', 0)} |
| AI回答数 | {conversation_data.get('assistant_messages', 0)} |

### 进展记录统计

| 指标 | 数值 |
|------|------|
| 总记录数 | {total_logs} |
| 家长参与度 | {engagement_text} |

**类别分布**:
"""

        for cat, count in categories.items():
            report += f"- {cat}: {count}条\n"

        report += f"""
### 进展趋势

{trend_text}，{main_concern}方面记录最多。

---

## 💡 专业建议

1. **保持记录习惯** - 定期记录孩子的表现有助于更好地跟踪进展
2. **关注{main_concern}** - 建议家长在日常生活中多关注这方面的发展
3. **坚持干预训练** - 持续性和一致性是干预成功的关键
4. **家校配合** - 建议与治疗师保持沟通，了解孩子在校/中心的表現

---

## 🎯 下周期目标

1. 继续保持每周至少2-3次的记录频率
2. 重点关注{main_concern}方面的进步
3. 与专业治疗师讨论当前干预计划

---

## ⚠️ 温馨提醒

- 本报告仅供参考，不能替代专业评估
- 如有疑问，请咨询BCBA或专业医生
- 每个孩子的发展节奏不同，请耐心陪伴

---

*本报告由ABA智能助手自动生成 | {datetime.now().strftime('%Y-%m-%d')}*
"""

        return report

    def generate_suggestions(
        self,
        child_info: Dict,
        progress_data: Dict
    ) -> List[str]:
        """生成个性化建议"""
        if not self.llm_client:
            return self._generate_fallback_suggestions(child_info, progress_data)

        prompt = f"""
孩子信息：{json.dumps(child_info, ensure_ascii=False)}
进展数据：{json.dumps(progress_data, ensure_ascii=False)}

请根据以上信息，生成3-5条针对这个孩子家长的个性化建议。要求：
- 建议要具体可操作
- 适合ABA干预场景
- 语言温暖专业
- 每条建议50字以内
"""

        try:
            response = self._call_llm(prompt)
            suggestions = [s.strip() for s in response.split('\n') if s.strip()]
            return suggestions[:5]
        except Exception:
            return self._generate_fallback_suggestions(child_info, progress_data)

    def _generate_fallback_suggestions(
        self,
        child_info: Dict,
        progress_data: Dict
    ) -> List[str]:
        """生成基础建议"""
        suggestions = [
            "保持定期记录孩子表现的习惯，有助于跟踪进展",
            "坚持每天的干预训练，保持一致性",
            "多与孩子进行互动游戏，促进社交发展",
            "保证充足的睡眠和规律的作息",
            "与治疗师保持密切沟通，了解孩子进步"
        ]

        engagement = progress_data.get('engagement_level', 'medium')
        if engagement == 'low':
            suggestions.insert(0, "建议增加与AI助手的互动频率")

        return suggestions


class SmartReportGenerator:
    """智能报告生成器（整合数据分析和AI）"""

    def __init__(self, child_manager, llm_provider: str = "minimax"):
        self.child_manager = child_manager
        self.ai_generator = AIReportGenerator(llm_provider)

    def generate_full_report(
        self,
        child_id: str,
        user_id: str,
        report_type: str = "月报",
        days: int = 30
    ) -> Dict:
        """生成完整报告"""

        period_end = datetime.now()
        period_start = period_end - timedelta(days=days)

        child = self.child_manager.get_child(child_id, user_id)
        if not child:
            return {"success": False, "error": "孩子档案不存在"}

        progress_summary = self.child_manager.get_progress_summary(
            child_id, user_id,
            start_date=period_start.strftime('%Y-%m-%d'),
            end_date=period_end.strftime('%Y-%m-%d')
        )

        conv_stats = self.child_manager.get_conversation_stats(
            child_id, user_id,
            start_date=period_start.strftime('%Y-%m-%d'),
            end_date=period_end.strftime('%Y-%m-%d')
        )

        logs = self.child_manager.get_progress_logs(
            child_id, user_id,
            start_date=period_start.strftime('%Y-%m-%d'),
            end_date=period_end.strftime('%Y-%m-%d'),
            limit=100
        )

        top_concerns = self._extract_top_concerns(logs)
        trend = self._analyze_trend(logs, period_start, period_end)
        engagement = self._calculate_engagement(conv_stats, len(logs))

        progress_data = {
            "total_logs": progress_summary.get("total_logs", 0),
            "by_category": progress_summary.get("by_category", {}),
            "top_concerns": top_concerns,
            "trend": trend,
            "engagement_level": engagement,
            "recent_logs": logs[:20]
        }

        conversation_data = {
            "total": conv_stats.get("total", 0),
            "user_messages": conv_stats.get("user_messages", 0),
            "assistant_messages": conv_stats.get("assistant_messages", 0)
        }

        report_content = self.ai_generator.generate_report_with_ai(
            child_info=child,
            progress_data=progress_data,
            conversation_data=conversation_data
        )

        summary = f"共记录{progress_data['total_logs']}条进展，对话{conversation_data['total']}轮次，整体{trend}"

        success, msg, report_id = self.child_manager.save_report(
            child_id=child_id,
            user_id=user_id,
            report_type=report_type,
            title=f"{child['name']} - {report_type} ({period_end.strftime('%Y-%m-%d')})",
            content=report_content,
            summary=summary,
            period_start=period_start.strftime('%Y-%m-%d'),
            period_end=period_end.strftime('%Y-%m-%d')
        )

        return {
            "success": success,
            "report_id": report_id if success else None,
            "content": report_content if success else None,
            "summary": summary if success else None,
            "progress_data": progress_data,
            "conversation_data": conversation_data,
            "error": msg if not success else None
        }

    def _extract_top_concerns(self, logs: List[Dict]) -> List[Dict]:
        """提取家长关注点"""
        concern_keywords = {
            "行为问题": ["发脾气", "哭闹", "攻击", "自伤", "行为"],
            "语言沟通": ["说话", "语言", "表达", "沟通", "词汇"],
            "社交互动": ["社交", "互动", "目光接触", "分享", "朋友"],
            "情绪管理": ["情绪", "焦虑", "崩溃", "挫折"],
            "日常生活": ["吃饭", "睡觉", "如厕", "自理", "穿衣服"]
        }

        concern_counts = {k: 0 for k in concern_keywords}

        for log in logs:
            desc = str(log.get("description", "")) + str(log.get("metric_name", ""))
            for concern, keywords in concern_keywords.items():
                if any(kw in desc for kw in keywords):
                    concern_counts[concern] += 1

        ranked = sorted(
            [(k, v) for k, v in concern_counts.items() if v > 0],
            key=lambda x: x[1],
            reverse=True
        )

        return [{"concern": k, "count": v} for k, v in ranked[:3]]

    def _analyze_trend(self, logs: List, start: datetime, end: datetime) -> str:
        """分析进展趋势"""
        if len(logs) < 3:
            return "insufficient_data"

        total_days = (end - start).days
        if total_days == 0:
            total_days = 1

        mid_point = start + timedelta(days=total_days // 2)

        first_half = sum(1 for log in logs if log.get("log_date", "")[:10] <= mid_point.strftime('%Y-%m-%d'))
        second_half = sum(1 for log in logs if log.get("log_date", "")[:10] > mid_point.strftime('%Y-%m-%d'))

        if second_half > first_half * 1.3:
            return "improving"
        elif second_half < first_half * 0.7:
            return "declining"
        else:
            return "stable"

    def _calculate_engagement(self, conv_stats: Dict, log_count: int) -> str:
        """计算参与度"""
        total = conv_stats.get("total", 0) + log_count

        if total < 5:
            return "low"
        elif total < 20:
            return "medium"
        else:
            return "high"
