"""
====================================
ABA智能助手 - AI报告生成模块
====================================

功能：
- 对话数据分析
- 进展趋势分析
- AI撰写个性化报告
- 可视化数据展示
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from core.deep_memory_extended import ChildProfileManager
from utils.task_generator import TaskGenerator


class ReportGenerator:
    """AI报告生成器"""

    def __init__(
        self,
        child_manager: ChildProfileManager,
        llm_client=None
    ):
        self.child_manager = child_manager
        self.llm_client = llm_client

    def generate_weekly_report(
        self,
        child_id: str,
        user_id: str
    ) -> Dict:
        """生成周报"""
        return self._generate_report(child_id, user_id, "周报", 7)

    def generate_monthly_report(
        self,
        child_id: str,
        user_id: str
    ) -> Dict:
        """生成月报"""
        return self._generate_report(child_id, user_id, "月报", 30)

    def generate_progress_report(
        self,
        child_id: str,
        user_id: str,
        days: int = 90
    ) -> Dict:
        """生成阶段报告"""
        return self._generate_report(child_id, user_id, "阶段报告", days)

    def _generate_report(
        self,
        child_id: str,
        user_id: str,
        report_type: str,
        days: int
    ) -> Dict:
        """核心报告生成逻辑"""
        period_end = datetime.now()
        period_start = period_end - timedelta(days=days)

        child = self.child_manager.get_child(child_id, user_id)
        if not child:
            return {"success": False, "error": "孩子档案不存在"}

        progress_logs = self.child_manager.get_progress_logs(
            child_id, user_id,
            start_date=period_start.strftime('%Y-%m-%d'),
            end_date=period_end.strftime('%Y-%m-%d'),
            limit=200
        )

        conv_stats = self.child_manager.get_conversation_stats(
            child_id, user_id,
            start_date=period_start.strftime('%Y-%m-%d'),
            end_date=period_end.strftime('%Y-%m-%d')
        )

        conversation_history = self._get_conversation_history(
            user_id, period_start, period_end
        )

        tasks = self.child_manager.get_tasks(
            child_id, user_id, limit=200
        )

        analysis = self._analyze_data(
            child=child,
            progress_logs=progress_logs,
            conv_stats=conv_stats,
            conversation_history=conversation_history,
            tasks=tasks,
            period_start=period_start,
            period_end=period_end
        )

        task_analysis = analysis.get("task_analysis", {})
        new_tasks = []
        if task_analysis.get("pending", 0) > 0 and task_analysis.get("completed", 0) > 0:
            task_gen = TaskGenerator()
            intervention_goals = child.get('intervention_goals', '')
            diagnosis = child.get('diagnosis', '')
            suggested_tasks = task_gen.generate_initial_tasks(intervention_goals, diagnosis)
            num_new = min(3, len(suggested_tasks))
            for task in suggested_tasks[:num_new]:
                s, m, tid = self.child_manager.add_task(
                    child_id=child_id,
                    user_id=user_id,
                    task_name=task["name"],
                    task_description=task.get("description", ""),
                    category=task.get("category", ""),
                    is_auto_generated=True
                )
                if s:
                    new_tasks.append(task["name"])

        report_content = self._compose_report(
            child=child,
            report_type=report_type,
            analysis=analysis,
            progress_logs=progress_logs,
            conv_stats=conv_stats,
            period_start=period_start,
            period_end=period_end,
            new_tasks=new_tasks
        )

        summary = self._generate_summary(analysis, child)

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
            "report_id": report_id,
            "content": report_content if success else None,
            "summary": summary if success else None,
            "analysis": analysis,
            "new_tasks": new_tasks,
            "error": msg if not success else None
        }

    def _get_conversation_history(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """获取对话历史"""
        try:
            from core.deep_memory import memory_system
            conn = memory_system.db_path
            import sqlite3

            conn_db = sqlite3.connect(conn)
            cursor = conn_db.cursor()

            cursor.execute(
                """SELECT role, content, timestamp FROM conversations
                   WHERE user_id = ? AND timestamp >= ? AND timestamp <= ?
                   ORDER BY timestamp""",
                (user_id, start_date.isoformat(), end_date.isoformat())
            )

            rows = cursor.fetchall()
            conn_db.close()

            return [
                {"role": row[0], "content": row[1], "timestamp": row[2]}
                for row in rows
            ]
        except Exception as e:
            print(f"获取对话历史失败: {e}")
            return []

    def _analyze_data(
        self,
        child: Dict,
        progress_logs: List[Dict],
        conv_stats: Dict,
        conversation_history: List[Dict],
        tasks: List[Dict],
        period_start: datetime,
        period_end: datetime
    ) -> Dict:
        """分析数据并提取洞察"""
        category_stats = {}
        for log in progress_logs:
            cat = log.get("category", "其他")
            if cat not in category_stats:
                category_stats[cat] = {"count": 0, "items": []}
            category_stats[cat]["count"] += 1
            category_stats[cat]["items"].append(log)

        user_questions = [
            msg["content"][:100] for msg in conversation_history
            if msg["role"] == "user"
        ]

        concern_patterns = self._extract_concern_patterns(user_questions)

        progress_trends = self._analyze_progress_trends(progress_logs)

        task_analysis = self._analyze_tasks(tasks, period_start, period_end)

        return {
            "category_stats": category_stats,
            "conv_stats": conv_stats,
            "total_log_days": len(set(
                log["log_date"][:10] for log in progress_logs if log.get("log_date")
            )),
            "concern_patterns": concern_patterns,
            "progress_trends": progress_trends,
            "engagement_level": self._calculate_engagement(conv_stats, progress_logs),
            "top_concerns": self._rank_concerns(concern_patterns),
            "task_analysis": task_analysis
        }

    def _analyze_tasks(
        self,
        tasks: List[Dict],
        period_start: datetime,
        period_end: datetime
    ) -> Dict:
        """分析任务数据"""
        if not tasks:
            return {
                "total": 0,
                "completed": 0,
                "pending": 0,
                "with_feedback": 0,
                "completion_rate": 0,
                "category_breakdown": {},
                "ineffective_tasks": [],
                "completed_tasks": []
            }

        period_start_str = period_start.strftime('%Y-%m-%d')
        period_end_str = period_end.strftime('%Y-%m-%d')

        period_tasks = [
            t for t in tasks
            if t.get('created_at', '')[:10] >= period_start_str
            and t.get('created_at', '')[:10] <= period_end_str
        ]

        if not period_tasks:
            period_tasks = tasks[:20]

        completed = [t for t in period_tasks if t.get('status') == 'completed']
        pending = [t for t in period_tasks if t.get('status') == 'pending']
        with_feedback = [t for t in period_tasks if t.get('feedback')]

        completion_rate = len(completed) / len(period_tasks) * 100 if period_tasks else 0

        category_breakdown = {}
        for t in period_tasks:
            cat = t.get('category', '未分类') or '未分类'
            if cat not in category_breakdown:
                category_breakdown[cat] = {"total": 0, "completed": 0, "pending": 0}
            category_breakdown[cat]["total"] += 1
            if t.get('status') == 'completed':
                category_breakdown[cat]["completed"] += 1
            else:
                category_breakdown[cat]["pending"] += 1

        ineffective_tasks = [
            t for t in period_tasks
            if t.get('feedback') == '没有效果'
        ]

        return {
            "total": len(period_tasks),
            "completed": len(completed),
            "pending": len(pending),
            "with_feedback": len(with_feedback),
            "completion_rate": round(completion_rate, 1),
            "category_breakdown": category_breakdown,
            "ineffective_tasks": ineffective_tasks,
            "completed_tasks": completed[-5:]
        }

    def _extract_concern_patterns(self, questions: List[str]) -> Dict[str, int]:
        """提取家长关注的问题模式"""
        patterns = {
            "行为问题": ["发脾气", "哭闹", "攻击", "自伤", "重复行为", "刻板"],
            "语言沟通": ["说话", "语言", "表达", "沟通", "词汇", "仿说"],
            "社交互动": ["社交", "互动", "交朋友", "目光接触", "分享"],
            "日常生活": ["吃饭", "睡觉", "如厕", "穿衣", "卫生"],
            "学习能力": ["学习", "注意力", "专注", "模仿", "认知"],
            "情绪管理": ["情绪", "挫折", "焦虑", "崩溃", "自我调节"]
        }

        concern_counts = {k: 0 for k in patterns}
        concern_examples = {k: [] for k in patterns}

        for q in questions:
            for concern, keywords in patterns.items():
                for kw in keywords:
                    if kw in q:
                        concern_counts[concern] += 1
                        if len(concern_examples[concern]) < 2:
                            concern_examples[concern].append(q[:50])
                        break

        return {
            "counts": concern_counts,
            "examples": concern_examples
        }

    def _analyze_progress_trends(self, logs: List[Dict]) -> Dict:
        """分析进展趋势"""
        if not logs:
            return {"trend": " insufficient_data", "details": {}}

        logs_by_date = {}
        for log in logs:
            date = log.get("log_date", "")[:10]
            if date:
                if date not in logs_by_date:
                    logs_by_date[date] = []
                logs_by_date[date].append(log)

        date_counts = {d: len(items) for d, items in logs_by_date.items()}

        if len(date_counts) < 2:
            return {"trend": "insufficient_data", "details": {}}

        sorted_dates = sorted(date_counts.keys())
        first_half = sum(date_counts[d] for d in sorted_dates[:len(sorted_dates)//2])
        second_half = sum(date_counts[d] for d in sorted_dates[len(sorted_dates)//2:])

        if second_half > first_half * 1.2:
            trend = "improving"
        elif second_half < first_half * 0.8:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "details": {
                "first_half_logs": first_half,
                "second_half_logs": second_half,
                "recording_frequency": len(date_counts)
            }
        }

    def _calculate_engagement(
        self,
        conv_stats: Dict,
        progress_logs: List[Dict]
    ) -> str:
        """计算家长参与度"""
        total_activities = conv_stats.get("total", 0) + len(progress_logs)

        if total_activities == 0:
            return "low"
        elif total_activities < 10:
            return "low"
        elif total_activities < 30:
            return "medium"
        else:
            return "high"

    def _rank_concerns(self, concern_patterns: Dict) -> List[Dict]:
        """排名家长关注点"""
        counts = concern_patterns.get("counts", {})
        ranked = sorted(
            [{"concern": k, "count": v} for k, v in counts.items() if v > 0],
            key=lambda x: x["count"],
            reverse=True
        )
        return ranked[:3]

    def _compose_report(
        self,
        child: Dict,
        report_type: str,
        analysis: Dict,
        progress_logs: List[Dict],
        conv_stats: Dict,
        period_start: datetime,
        period_end: datetime,
        new_tasks: List[str] = None
    ) -> str:
        """撰写完整报告"""
        if new_tasks is None:
            new_tasks = []
        trend_emoji = {
            "improving": "📈",
            "declining": "📉",
            "stable": "➡️",
            "insufficient_data": "➖"
        }
        trend_text = {
            "improving": "进步趋势",
            "declining": "需要关注",
            "stable": "保持稳定",
            "insufficient_data": "数据不足"
        }

        engagement_text = {
            "high": "高度参与",
            "medium": "中等参与",
            "low": "参与较少"
        }

        report = f"""
# {child['name']} - {report_type}

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**报告周期**: {period_start.strftime('%Y-%m-%d')} ~ {period_end.strftime('%Y-%m-%d')}

---

## 📋 基本信息

| 项目 | 内容 |
|------|------|
| 姓名 | {child['name']} |
| 出生日期/年龄 | {child.get('birth_date', '未记录')} |
| 诊断 | {child.get('diagnosis', '未记录')} |
| 干预目标 | {child.get('intervention_goals', '未记录')} |

---

## 📊 数据概览

### 对话互动统计

| 指标 | 数值 |
|------|------|
| AI对话总轮次 | {conv_stats.get('total', 0)} |
| 家长提问数 | {conv_stats.get('user_messages', 0)} |
| AI回答数 | {conv_stats.get('assistant_messages', 0)} |

### 进展记录统计

| 指标 | 数值 |
|------|------|
| 记录总条数 | {len(progress_logs)} |
| 有记录的天数 | {analysis.get('total_log_days', 0)} |
| 家长参与度 | {engagement_text.get(analysis.get('engagement_level', 'medium'), '中等')} |

### 各类别记录分布

| 类别 | 记录数 |
|------|--------|
"""

        for cat, stats in analysis.get("category_stats", {}).items():
            report += f"| {cat} | {stats['count']} |\n"

        task_analysis = analysis.get("task_analysis", {})
        if task_analysis.get("total", 0) > 0:
            report += f"""
### 任务完成情况

| 指标 | 数值 |
|------|------|
| 任务总数 | {task_analysis.get('total', 0)} |
| 已完成 | {task_analysis.get('completed', 0)} |
| 待完成 | {task_analysis.get('pending', 0)} |
| 完成率 | {task_analysis.get('completion_rate', 0)}% |
| 已反馈 | {task_analysis.get('with_feedback', 0)} |

"""
            if task_analysis.get("category_breakdown"):
                report += f"""
**任务类别分布**：

| 类别 | 完成 | 待完成 |
|------|------|--------|
"""
                for cat, data in task_analysis.get("category_breakdown", {}).items():
                    report += f"| {cat} | {data.get('completed', 0)} | {data.get('pending', 0)} |\n"

            completed_tasks = task_analysis.get("completed_tasks", [])
            if completed_tasks:
                report += f"""

**已完成的任务示例**：
"""
                for t in completed_tasks[:3]:
                    report += f"- ✅ {t.get('task_name', '未知任务')}\n"

            ineffective_tasks = task_analysis.get("ineffective_tasks", [])
            if ineffective_tasks:
                report += f"""

**需要关注的任务**（效果不佳）：
"""
                for t in ineffective_tasks[:3]:
                    report += f"- ⚠️ {t.get('task_name', '未知任务')} - {t.get('feedback_note', '无备注')}\n"

        report += f"""
---

## 🔍 深度分析

### 1. 进展趋势分析

**整体趋势**: {trend_emoji.get(analysis.get('progress_trends', {}).get('trend', 'insufficient_data'), '➖')} {trend_text.get(analysis.get('progress_trends', {}).get('trend', 'insufficient_data'), '数据不足')}

"""

        trend_details = analysis.get("progress_trends", {}).get("details", {})
        if trend_details:
            report += f"""
- 前半周期记录数: {trend_details.get('first_half_logs', 0)} 条
- 后半周期记录数: {trend_details.get('second_half_logs', 0)} 条
- 记录频率: 约 {trend_details.get('recording_frequency', 0)} 天
"""

        top_concerns = analysis.get("top_concerns", [])
        if top_concerns:
            report += f"""
### 2. 家长关注点分析

本周期内，您最关注的话题是：

"""
            for i, item in enumerate(top_concerns, 1):
                report += f"{i}. **{item['concern']}** ({item['count']}次相关讨论)\n"

            concern_examples = analysis.get("concern_patterns", {}).get("examples", {})
            for item in top_concerns:
                examples = concern_examples.get(item['concern'], [])
                if examples:
                    report += f"\n   示例问题：\n"
                    for ex in examples[:1]:
                        report += f"   - \"{ex}...\"\n"

        report += """
---

## 💡 专业建议

"""

        suggestions = self._generate_suggestions(child, analysis)
        for i, suggestion in enumerate(suggestions, 1):
            report += f"{i}. {suggestion}\n\n"

        report += f"""
---

## 📝 下周期目标

基于本周期的情况，建议下周期重点关注：

"""

        next_goals = self._generate_next_goals(child, analysis)
        for i, goal in enumerate(next_goals, 1):
            report += f"{i}. {goal}\n"

        if new_tasks:
            report += f"""
### 🎯 下周期新任务清单

根据本周期完成情况，自动生成以下新任务：

"""
            for task in new_tasks:
                report += f"- [ ] {task}\n"
            report += "\n请在任务清单中查看并反馈完成情况\n"

        report += f"""

---

## ⚠️ 重要提醒

- 本报告仅供参考，不能替代专业评估
- 如有疑问，请咨询BCBA或专业医生
- 建议每周至少记录2-3次孩子的进展

---

*本报告由ABA智能助手自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

        return report

    def _generate_suggestions(self, child: Dict, analysis: Dict) -> List[str]:
        """生成专业建议"""
        suggestions = []
        engagement = analysis.get("engagement_level", "medium")
        trend = analysis.get("progress_trends", {}).get("trend", "stable")

        if engagement == "low":
            suggestions.append(
                "建议增加与AI助手的互动频率，定期记录孩子的表现有助于更好地跟踪进展。"
            )

        if trend == "declining":
            suggestions.append(
                "注意到记录频率有所下降，建议与治疗师讨论当前干预计划是否需要调整。"
            )

        top_concerns = analysis.get("top_concerns", [])
        if top_concerns:
            main_concern = top_concerns[0]['concern']
            if main_concern == "行为问题":
                suggestions.append(
                    "关于行为问题，建议继续使用正向强化策略，记录行为发生的前因后果。"
                )
            elif main_concern == "语言沟通":
                suggestions.append(
                    "语言发展需要持续的语言环境刺激，可以在日常生活中创造更多交流机会。"
                )
            elif main_concern == "社交互动":
                suggestions.append(
                    "社交技能训练建议从一对一开始，逐步过渡到小组环境。"
                )

        if not suggestions:
            suggestions.append("继续保持当前良好的干预节奏，定期评估孩子的发展情况。")

        return suggestions[:4]

    def _generate_next_goals(self, child: Dict, analysis: Dict) -> List[str]:
        """生成下周期目标"""
        goals = []
        intervention_goals = child.get('intervention_goals', '')
        top_concerns = analysis.get("top_concerns", [])
        task_analysis = analysis.get("task_analysis", {})

        if intervention_goals:
            goals.append(f"继续推进干预目标：{intervention_goals[:50]}...")

        pending_tasks = task_analysis.get("pending", 0)
        if pending_tasks > 0:
            ineffective = task_analysis.get("ineffective_tasks", [])
            if ineffective:
                goals.append(f"调整{len(ineffective)}个效果不佳的任务，尝试不同策略")
            completed = task_analysis.get("completed", 0)
            if completed > 0:
                goals.append(f"继续完成剩余{pending_tasks}个进行中的任务")

        category_breakdown = task_analysis.get("category_breakdown", {})
        for cat, data in category_breakdown.items():
            if data.get("pending", 0) > 0 and cat != "未分类":
                goals.append(f"加强'{cat}'方面的练习")

        if top_concerns:
            main_concern = top_concerns[0]['concern']
            goals.append(f"重点关注{main_concern}方面的进展")

        goals.append("保持每周至少2-3次的进展记录")

        return goals[:5]

    def _generate_summary(self, analysis: Dict, child: Dict) -> str:
        """生成报告摘要"""
        total_logs = sum(
            stats["count"]
            for stats in analysis.get("category_stats", {}).values()
        )
        conv_total = analysis.get("conv_stats", {}).get("total", 0)
        trend = analysis.get("progress_trends", {}).get("trend", "稳定")
        engagement = analysis.get("engagement_level", "中等")
        task_analysis = analysis.get("task_analysis", {})

        summary = f"本周期共记录{total_logs}条进展，对话{conv_total}轮次。"
        summary += f"任务完成率{task_analysis.get('completion_rate', 0)}%。"
        summary += f"整体{trend}，家长参与度{engagement}。"

        return summary


class ProgressChart:
    """进展图表生成器"""

    @staticmethod
    def generate_category_chart(progress_logs: List[Dict]) -> str:
        """生成类别分布图表（文本格式）"""
        categories = {}
        for log in progress_logs:
            cat = log.get("category", "其他")
            categories[cat] = categories.get(cat, 0) + 1

        if not categories:
            return "暂无数据"

        chart = "类别分布:\n"
        max_count = max(categories.values())

        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            bar_length = int(count / max_count * 20)
            bar = "█" * bar_length
            chart += f"  {cat}: {bar} ({count})\n"

        return chart

    @staticmethod
    def generate_timeline(progress_logs: List[Dict], limit: int = 10) -> str:
        """生成时间线（文本格式）"""
        if not progress_logs:
            return "暂无数据"

        timeline = "最近进展:\n"

        sorted_logs = sorted(
            progress_logs,
            key=lambda x: x.get("log_date", ""),
            reverse=True
        )[:limit]

        for i, log in enumerate(sorted_logs, 1):
            date = log.get("log_date", "未知")[:10]
            cat = log.get("category", "其他")
            desc = log.get("description", log.get("metric_name", ""))[:30]
            timeline += f"  {i}. {date} | {cat} | {desc}\n"

        return timeline
