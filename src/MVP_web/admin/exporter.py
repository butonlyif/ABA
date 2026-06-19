"""
单用户数据导出器

输出两份文件到 data/users/exports/{user_id}/{timestamp}/：
  - user_data.md   结构化 markdown，便于专家快速浏览
  - user_data.json 结构化原始数据

设计原则：
  - 只保留重要信息，去掉冗余字段（child_id、系统元数据、嵌套空对象）
  - 对话内容完整保留，不做截断
  - 人生教练与 ABA 数据在同一份报告内，方便综合分析
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple


def _s(val) -> str:
    return "" if val is None else str(val)


def build_markdown(bundle: Dict) -> str:
    user = bundle["user"]
    coach = bundle.get("coach") or {}
    sections = [
        _user_section(user),
        _children_section(bundle["children"]),
        _conversations_section(bundle["conversations"]),
        _coach_section(coach),
        _reports_section(bundle["reports"]),
    ]
    return "\n\n".join(sections) + "\n"


def _user_section(user: Dict) -> str:
    info = user.get("user_info") or {}
    lines = [
        "## 用户信息",
        f"- 用户名：{_s(user.get('username'))}",
        f"- 注册时间：{_s(user.get('created_at'))[:10]}",
        f"- 最近登录：{_s(user.get('last_login'))[:16]}",
    ]
    if info:
        lines.append("\n### 孩子信息")
        for k, v in info.items():
            if v:
                lines.append(f"- {k}：{_s(v)}")
    return "\n".join(lines)


def _children_section(children: list) -> str:
    if not children:
        return "## 孩子档案\n\n_（无记录）_"
    parts = []
    for i, c in enumerate(children, 1):
        parts.append(
            f"### {i}. {c.get('name') or '未命名'}\n"
            f"- 出生日期：{_s(c.get('birth_date'))}\n"
            f"- 诊断：{_s(c.get('diagnosis'))}\n"
            f"- 状态：{_s(c.get('status'))}\n"
            f"- 干预目标：{_s(c.get('intervention_goals')) or '未填写'}\n"
            f"- 备注：{_s(c.get('notes')) or '无'}"
        )
    return "## 孩子档案\n\n" + "\n\n".join(parts)


def _conversations_section(convs: list) -> str:
    if not convs:
        return "## ABA 对话\n\n_（无对话）_"
    parts = []
    last_date = None
    for c in convs:
        ts = _s(c.get("timestamp"))
        date_part = ts[:10]
        if date_part != last_date:
            parts.append(f"\n### {date_part}\n")
            last_date = date_part
        role = c.get("role", "?")
        role_label = {"user": "家长", "assistant": "AI助手"}.get(role, role)
        content = _s(c.get("content"))
        parts.append(f"**[{ts[11:]}] {role_label}：** {content}")
    return "## ABA 对话\n\n_（共 {} 条）_\n\n".format(len(convs)) + "\n".join(parts)


def _coach_section(coach: Dict) -> str:
    if not coach:
        return "## 人生教练数据\n\n_（未使用人生教练模块）_"
    parts = ["## 人生教练数据"]
    parts.append("")  # blank line

    # 心情记录
    moods = coach.get("mood_log", [])
    if moods:
        rows = []
        for m in moods:
            rows.append(
                f"- **{m.get('time', '')}** "
                f"{m.get('emoji', '')} {m.get('label', '')} "
                f"(评分 {m.get('score', '-')}/4, 强度 {m.get('intensity', '-')}/10)"
            )
            trigger = m.get("trigger", "")
            if trigger:
                rows.append(f"  触发：{trigger[:60]}")
            note = m.get("note", "")
            if note:
                rows.append(f"  备注：{note[:60]}")
        parts.append("### 心情记录（共 {} 条）\n".format(len(moods)))
        parts.extend(rows)
    else:
        parts.append("### 心情记录\n_（无记录）_")

    # 个人记录
    records = coach.get("personal_records", [])
    if records:
        rows = []
        for r in records:
            icon = r.get("type_icon", "")
            rows.append(
                f"- **{r.get('time', '')}** {icon} {r.get('type', '')}："
                f"{r.get('title', '')} — {r.get('content', '')[:80]}"
            )
        parts.append("\n### 个人记录（共 {} 条）\n".format(len(records)))
        parts.extend(rows)
    else:
        parts.append("\n### 个人记录\n_（无记录）_")

    # 成长项目
    projects = coach.get("growth_projects", [])
    tasks_done = coach.get("_tasks_done_root", [])
    stage = coach.get("growth_stage", 0)
    if projects or tasks_done:
        parts.append("\n### 成长项目（共 {} 项，阶段 {}）".format(len(projects), stage))
        for proj in projects:
            parts.append(
                f"- **{proj.get('issue', '未命名项目')}** "
                f"[{proj.get('status', 'active')}] 创建于 {proj.get('created_at', '')}"
            )
        if tasks_done:
            parts.append("  已完成任务：")
            for task in tasks_done:
                parts.append(f"  ✅ {task.get('text', task.get('id', ''))}")
        else:
            parts.append("  （尚无完成任务）")
    else:
        parts.append("\n### 成长项目\n_（无记录）_")

    # 教练对话
    msgs = coach.get("coach_messages", [])
    if msgs:
        parts.append(f"\n### 教练对话（共 {len(msgs)} 条）")
        for m in msgs:
            role = "👤 用户" if m.get("role") == "user" else "🤖 教练"
            parts.append(f"**[{m.get('time', '')}] {role}：**")
            parts.append(m.get("content", "")[:300])
            parts.append("")
    else:
        parts.append("\n### 教练对话\n_（无记录）_")

    return "\n".join(parts)


def _reports_section(reports: list) -> str:
    if not reports:
        return "## 历史报告\n\n_（无报告）_"
    parts = ["## 历史报告"]
    for r in reports:
        summary = _s(r.get("summary", ""))
        content = _s(r.get("content", ""))
        parts.append(
            f"\n### {r.get('title', '报告')} "
            f"[{_s(r.get('report_type'))}] "
            f"{_s(r.get('created_at'))[:10]}\n"
            f"\n{summary}\n\n"
            f"{content}"
        )
    return "\n".join(parts)


def export_user(bundle: Dict, exports_root: Path) -> Tuple[Path, Path]:
    user_id = bundle["user"]["user_id"]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = exports_root / user_id / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / "user_data.md"
    json_path = out_dir / "user_data.json"

    md_path.write_text(build_markdown(bundle), encoding="utf-8")
    json_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return md_path, json_path