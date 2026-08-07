"""为 AI 对话构造用户上下文（T8：让 AI 记得用户的情况）。

coach 场景：用户最近情绪趋势 + 日记摘要。

设计原则：
- 路由层调用，service 层只负责纯函数式拼接
- 输出简洁文本（注入 system prompt，太长会浪费 token）
- 数据缺失时返回 None（不污染 prompt）
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from app.models import JournalEntry, MoodEntry


def build_coach_context(moods: Iterable["MoodEntry"], journals: Iterable["JournalEntry"]) -> str | None:
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
