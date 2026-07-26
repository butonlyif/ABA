"""为 AI 对话构造用户上下文（T8：让 AI 记得用户的情况）。

不引入向量数据库，只做结构化数据拼接：
- aba 场景：孩子档案 + 最近训练摘要
- coach 场景：用户最近情绪趋势 + 日记摘要

设计原则：
- 路由层调用，service 层只负责纯函数式拼接
- 输出简洁文本（注入 system prompt，太长会浪费 token）
- 数据缺失时返回 None（不污染 prompt）
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from ..models import Child, JournalEntry, MoodEntry, TrainingSession


def _age_years(birth_date) -> int | None:
    if not birth_date:
        return None
    try:
        today = date.today()
        years = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return years if years >= 0 else None
    except Exception:
        return None


def build_aba_context(child: Child | None, recent_sessions: Iterable[TrainingSession] = ()) -> str | None:
    """ABA 场景：孩子档案 + 最近训练摘要。"""
    if not child:
        return None
    parts: list[str] = []
    age = _age_years(child.birth_date)
    parts.append(f"孩子姓名：{child.name}" + (f"（{age}岁）" if age is not None else ""))
    if child.diagnosis:
        parts.append(f"诊断：{child.diagnosis}")
    if child.goals:
        parts.append(f"干预目标：{child.goals[:200]}")
    snapshot = child.status_snapshot or {}
    if isinstance(snapshot, dict):
        domains = snapshot.get("domains") or {}
        if domains:
            top = sorted(domains.items(), key=lambda x: x[1])[:3]
            parts.append("较弱能力域：" + "、".join(f"{k}({v})" for k, v in top))
    sessions = list(recent_sessions)
    if sessions:
        last = sessions[0]
        parts.append(f"最近一次训练：{last.skill_name}（{last.created_at.date()}）")
        if len(sessions) >= 2:
            parts.append(f"近 {len(sessions)} 次训练覆盖技能：{', '.join(sorted({s.skill_name for s in sessions}))}")
    return "\n".join(parts) if len(parts) > 1 else None


def build_coach_context(moods: Iterable[MoodEntry], journals: Iterable[JournalEntry]) -> str | None:
    """教练场景：仅提供家长本人的近期情绪与反思，不注入孩子或 ABA 信息。"""
    mood_list = list(moods)
    journal_list = list(journals)
    if not mood_list and not journal_list:
        return None
    parts: list[str] = []
    if mood_list:
        parts.append(f"用户本人最近 {len(mood_list)} 条情绪：" + "、".join(f"{m.mood}(强度{m.intensity})" for m in mood_list[:5]))
    if journal_list:
        latest = journal_list[0]
        parts.append(f"用户本人最新反思（{latest.created_at.date()}）：{latest.content[:80]}")
    return "\n".join(parts) if parts else None
