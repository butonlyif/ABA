"""人生教练 AI 周报。

数据源：MoodEntry / JournalEntry / coach 产品的 ChatMessage（指定周内）。
策略：优先调用 MiniMax LLM 生成个性化、有共情的周报；LLM 不可用时降级到规则版。
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

import httpx

from ..config import get_settings
from ..models import ChatMessage, JournalEntry, MoodEntry
from .ai import AiCall, _hotlines_block  # 复用 T2 的热线块（不导出常量避免污染）

# 情绪打分（与旧平台 mood_labels_7 保持一致），用于把字符串情绪映射成 1-7 分
_MOOD_SCORE = {
    "很差": 1, "不好": 2, "一般": 3, "还好": 4, "不错": 5, "平静": 6, "很好": 7,
}


def _week_range(week_offset: int = 0) -> tuple[date, date]:
    """返回 week_offset 周（0=本周，-1=上周）对应的 [周一, 周日]。"""
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _mood_score(mood: str) -> int:
    return _MOOD_SCORE.get(mood, 4)


def _build_prompt(
    week_label: str,
    moods: Iterable[MoodEntry],
    journals: Iterable[JournalEntry],
    chat_count: int,
) -> tuple[str, list[dict]]:
    """构造 LLM prompt + 用户数据摘要。返回 (system_prompt, user_content)。"""
    mood_list = list(moods)
    journal_list = list(journals)

    parts: list[str] = [f"时间范围：{week_label}"]
    parts.append(f"本周情绪记录 {len(mood_list)} 条，反思日记 {len(journal_list)} 篇，与教练对话 {chat_count} 次。")

    if mood_list:
        scores = [_mood_score(m.mood) for m in mood_list]
        avg = sum(scores) / len(scores)
        parts.append(f"情绪平均分 {avg:.1f}/7（1=很差，7=很好），平均强度 {sum(m.intensity for m in mood_list) / len(mood_list):.1f}/10。")
        parts.append("本周情绪条目：" + "；".join(f"{m.entry_date.isoformat()} {m.mood}(强度{m.intensity}){(' 备注:' + m.note) if m.note else ''}" for m in mood_list[:10]))
    else:
        parts.append("本周暂无情绪记录。")

    if journal_list:
        parts.append("本周反思日记：" + "\n".join(f"- {j.content[:120]}" for j in journal_list[:5]))

    system = (
        "你是温暖、不评判的家长陪伴教练。根据家长本周的情绪/日记/对话数据，"
        "写一份简短的周报（300-500 字），用中文，包含：\n"
        "1. 一段温柔的总结，看见 ta 这周的状态（避免说教，先共情）\n"
        "2. 观察 ta 这周的一个积极信号或值得肯定的点\n"
        "3. 给出 2 条具体、可执行的小建议（不是命令，是邀请）\n"
        "如果数据很少，承认这一点，并温柔鼓励记录的重要性。\n"
        "不要做医学诊断。如果检测到强烈痛苦信号，在结尾附上心理援助热线。"
    )
    return system, "\n".join(parts)


def _rule_based(
    week_label: str,
    moods: Iterable[MoodEntry],
    journals: Iterable[JournalEntry],
    chat_count: int,
) -> str:
    """规则版周报（LLM 不可用时的降级）。参照旧平台模板。"""
    mood_list = list(moods)
    journal_list = list(journals)
    lines: list[str] = [f"**{week_label} 周报**", ""]

    if mood_list:
        scores = [_mood_score(m.mood) for m in mood_list]
        avg = sum(scores) / len(scores)
        avg_int = sum(m.intensity for m in mood_list) / len(mood_list)
        lines.append(f"**情绪概况**：本周记录 {len(mood_list)} 次情绪，平均 {avg:.1f}/7，强度 {avg_int:.1f}/10。")
        if avg >= 6:
            lines.append("整体状态不错，保持让你平静的活动，并在日记里写下是什么帮到了你。")
        elif avg <= 3:
            lines.append("本周心情偏低，建议每天 3 分钟呼吸练习；持续低落可考虑多和教练聊聊，或寻求专业支持。")
        else:
            lines.append("情绪中等波动，作为照护者这是正常的——允许自己有起伏。")
    else:
        lines.append("本周暂无情绪记录。记录情绪是理解自己的第一步，建议每天至少一次。")

    if journal_list:
        lines.append(f"\n**反思日记**：写了 {len(journal_list)} 篇，继续保持这种觉察。")
    else:
        lines.append("\n**反思日记**：本周还没写。试着每天留一句话给今天的自己。")

    if chat_count > 0:
        lines.append(f"\n**与教练对话**：{chat_count} 次。和教练交流是觉察情绪、获得支持的重要方式。")
    else:
        lines.append("\n**与教练对话**：本周还没有对话。需要时随时来这里聊聊。")

    lines.append("\n**💡 本周建议**")
    lines.append("- 回顾本周的成长进度，哪怕完成一个小任务也是进步。")
    lines.append("- 记住：成长不是直线，波动是正常的。重要的是你一直在努力。")
    if mood_list and sum(_mood_score(m.mood) for m in mood_list) / len(mood_list) <= 3:
        lines.append(f"\n心理援助热线：\n{_hotlines_block()}")
    return "\n".join(lines)


def generate_weekly_summary(
    moods: Iterable[MoodEntry],
    journals: Iterable[JournalEntry],
    chat_count: int,
    week_offset: int = 0,
) -> tuple[str, AiCall]:
    """生成教练周报，返回 (content, AiCall)。优先 LLM，降级规则版。"""
    monday, sunday = _week_range(week_offset)
    week_label = f"{monday.strftime('%m月%d日')} - {sunday.strftime('%m月%d日')}"
    moods = list(moods)
    journals = list(journals)

    settings = get_settings()
    started = datetime.now(timezone.utc)

    if not settings.minimax_api_key:
        return _rule_based(week_label, moods, journals, chat_count), AiCall(
            "local", "rule-based", True, True,
            latency_ms=round((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        )

    system, user_content = _build_prompt(week_label, moods, journals, chat_count)
    try:
        response = httpx.post(
            f"{settings.minimax_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.minimax_api_key}"},
            json={"model": settings.minimax_model, "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ], "temperature": 0.6},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        answer = payload["choices"][0]["message"]["content"]
        answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.S).strip()
        usage = payload.get("usage", {})
        return answer or _rule_based(week_label, moods, journals, chat_count), AiCall(
            "minimax", settings.minimax_model, True, False,
            prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
            completion_tokens=int(usage.get("completion_tokens", 0) or 0),
            latency_ms=round((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        )
    except Exception as exc:
        return _rule_based(week_label, moods, journals, chat_count), AiCall(
            "minimax", settings.minimax_model, False, True,
            latency_ms=round((datetime.now(timezone.utc) - started).total_seconds() * 1000),
            error_type=type(exc).__name__,
        )
