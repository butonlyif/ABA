"""
管理员视角的报告草稿生成器

与主 app 的 report_generator / ai_report_generator 区别：
- 主 app 输出"家长向"周报/月报，温暖、鼓励、口语化
- 这里输出"专家审阅向"草稿：临床观察、行为模式、干预假设、风险点、待沟通事项
- 输入是已经汇总好的 bundle，不再回查 ChildProfileManager
- 可选注入"跨用户相似案例"作为参考上下文（RAG 风格）

落盘：data/users/drafts/{user_id}/{timestamp}.md
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .llm import AdminLLM, LLMUnavailable


SYSTEM_PROMPT = """你是一位 BCBA 级别的 ABA（应用行为分析）督导专家，同时具备心理咨询/亲子教练背景。
你正在为一名运营/督导审阅一名自闭症儿童家长的综合干预数据——包括 ABA 对话、成长项目、心情记录、教练对话等。

你的输出**不是给家长看的**，而是给专家审阅的草稿。要求：
1. 客观、专业，避免家长向报告那种"加油打气"的语气
2. 明确区分"事实"和"推断"——推断必须标注依据
3. 主动指出 ABA 干预数据和家长心理状态之间的关联或矛盾
4. 指出数据中的缺口、矛盾、可能被忽略的风险点
5. 给出"下一步建议的评估/观察项"，而不是直接下结论
6. 用 markdown 输出，结构清晰

输出固定包含以下章节：
- 一、个案概览
- 二、ABA 临床观察（基于对话与任务数据）
- 三、家长心理状态（基于人生教练数据：心情记录、成长项目、教练对话）
- 四、行为模式与干预假设
- 五、风险点 / 需特别关注
- 六、待与家长沟通的事项
- 七、数据缺口与建议补充的观察"""


def _truncate(text: str, n: int) -> str:
    if not text:
        return ""
    return text if len(text) <= n else text[:n] + "…(已截断)"


def _summarize_bundle_for_prompt(bundle: Dict, max_conv_chars: int = 6000) -> str:
    """把 bundle 浓缩成可塞进 prompt 的文本（含 ABA + 人生教练）。"""
    user = bundle["user"]
    info = user.get("user_info") or {}
    children = bundle["children"]
    convs = bundle["conversations"]
    tasks = bundle["tasks"]
    logs = bundle["progress_logs"]
    reports = bundle["reports"]
    coach = bundle.get("coach") or {}

    out = []
    out.append("## 用户档案")
    out.append(f"- 用户名：{user.get('username')}")
    out.append(f"- 注册：{user.get('created_at')}  最近登录：{user.get('last_login')}")
    if info:
        for k, v in info.items():
            if v:
                out.append(f"  - {k}: {v}")

    out.append("\n## 孩子档案")
    if children:
        for i, c in enumerate(children, 1):
            out.append(
                f"{i}. {c.get('name')} | 诊断: {c.get('diagnosis')} | "
                f"目标: {c.get('intervention_goals')} | "
                f"更新: {c.get('updated_at')}"
            )
    else:
        out.append("（无）")

    out.append("\n## 任务与反馈")
    if tasks:
        for t in tasks:
            out.append(
                f"- [{t.get('status')}] {t.get('task_name')} ({t.get('category')}) "
                f"反馈: {t.get('feedback')} 备注: {t.get('feedback_note') or '无'}"
            )
    else:
        out.append("（无）")

    out.append("\n## 进展记录")
    if logs:
        for log in logs:
            out.append(
                f"- {log.get('log_date')} [{log.get('category')}] "
                f"{log.get('metric_name')}={log.get('value')} {log.get('description') or ''}"
            )
    else:
        out.append("（无）")

    out.append("\n## 历史报告（最近 3 份）")
    if reports:
        for r in reports[:3]:
            out.append(f"### {r.get('title')} ({r.get('report_type')})")
            out.append(f"摘要：{r.get('summary')}")
    else:
        out.append("（无）")

    out.append("\n## 对话记录（最近 30 条）")
    conv_lines = []
    for c in convs[-30:]:
        role = c.get("role")
        role_label = {"user": "家长", "assistant": "AI"}.get(role, role)
        conv_lines.append(f"[{c.get('timestamp')}] {role_label}: {c.get('content', '')}")
    conv_text = "\n\n".join(conv_lines)
    out.append(_truncate(conv_text, max_conv_chars))

    # ---- 人生教练数据 ----
    out.append("\n" + "=" * 40)
    out.append("## 人生教练数据")
    out.append("=" * 40)

    if not coach:
        out.append("（未使用人生教练模块）")
    else:
        # 心情记录摘要
        moods = coach.get("mood_log", [])
        if moods:
            labels = {}
            for m in moods:
                lbl = m.get("label", "未知")
                labels[lbl] = labels.get(lbl, 0) + 1
            label_str = " | ".join(f"{k}×{v}" for k, v in sorted(labels.items(), key=lambda x: -x[1]))
            scores = [m.get("score", 4) for m in moods if m.get("score")]
            avg = sum(scores) / len(scores) if scores else 0
            out.append(f"\n### 心情记录（共 {len(moods)} 条）")
            out.append(f"- 平均分：{avg:.1f}/4 | 心情分布：{label_str}")
            for m in moods[-5:]:
                out.append(
                    f"  {m.get('time','')} {m.get('emoji','')} {m.get('label','')} "
                    f"(评分{m.get('score','')}, 强度{m.get('intensity','')}) "
                    f"触发：{m.get('trigger','')[:50]}"
                )
        else:
            out.append("\n### 心情记录（无）")

        # 个人记录摘要
        records = coach.get("personal_records", [])
        if records:
            out.append(f"\n### 个人记录（共 {len(records)} 条）")
            for r in records[-5:]:
                out.append(f"- {r.get('time','')} {r.get('type_icon','')} {r.get('type','')}：{r.get('title','')}")
                out.append(f"  {r.get('content','')[:100]}")
        else:
            out.append("\n### 个人记录（无）")

        # 成长项目
        projects = coach.get("growth_projects", [])
        tasks_done = coach.get("_tasks_done_root", [])
        stage = coach.get("growth_stage", 0)
        if projects:
            out.append(f"\n### 成长项目（共 {len(projects)} 项，阶段 {stage}）")
            for proj in projects:
                out.append(
                    f"- **{proj.get('issue', '未命名')}** "
                    f"[{proj.get('status', 'active')}] 创建于 {proj.get('created_at','')}"
                )
            if tasks_done:
                out.append("  已完成任务：")
                for task in tasks_done:
                    out.append(f"  ✅ {task.get('text', task.get('id',''))}")
            else:
                out.append("  （尚无完成任务）")
        else:
            out.append("\n### 成长项目（无）")

        # 教练对话（最近 8 条）
        msgs = coach.get("coach_messages", [])
        if msgs:
            out.append(f"\n### 教练对话（共 {len(msgs)} 条，展示最近 8 条）")
            for m in msgs[-8:]:
                role = "👤 用户" if m.get("role") == "user" else "🤖 教练"
                out.append(f"[{m.get('time','')}] {role}：{m.get('content','')[:200]}")
        else:
            out.append("\n### 教练对话（无）")

    return "\n".join(out)


def _format_similar_context(similar: List[Dict], max_chars: int = 4000) -> str:
    """把 find_similar 的结果格式化进 prompt。"""
    if not similar:
        return "（系统未检索到可参考的相似案例）"
    lines = []
    char_budget = max_chars
    for i, item in enumerate(similar, 1):
        meta = item.get("metadata") or {}
        header = (
            f"### 参考 {i} — {item['collection']} "
            f"(user={meta.get('username', '?')}, type={meta.get('type', '?')}, "
            f"distance={item['distance']:.3f})"
        )
        body = _truncate(item.get("document", ""), 1500)
        chunk = header + "\n" + body + "\n"
        if len(chunk) > char_budget:
            break
        lines.append(chunk)
        char_budget -= len(chunk)
    return "\n".join(lines) if lines else "（参考案例已被截断）"


def build_draft_prompt(
    bundle: Dict,
    similar_context: List[Dict],
) -> str:
    """组装最终 prompt。"""
    bundle_text = _summarize_bundle_for_prompt(bundle)
    similar_text = _format_similar_context(similar_context)

    prompt = f"""# 待审阅的儿童数据

{bundle_text}

# 跨用户相似案例参考（来自其他用户的孩子档案 / 报告 / 对话）

⚠️ 仅作参考，不要把参考案例的细节当成本孩子的事实。

{similar_text}

---

请按系统提示中规定的七个章节产出**专家审阅向草稿**。
输出请用 markdown。"""
    return prompt


def generate_draft(
    bundle: Dict,
    similar_context: Optional[List[Dict]] = None,
    llm: Optional[AdminLLM] = None,
) -> str:
    """
    生成 markdown 草稿。
    遇到 LLM 未配置，会抛 LLMUnavailable，由调用方决定怎么提示用户。
    """
    if llm is None:
        llm = AdminLLM()
    if not llm.available:
        raise LLMUnavailable(
            "LLM 未配置。请设置 MINIMAX_API_KEY 或切换 ABA_ADMIN_LLM=openai 并配置 OPENAI_API_KEY"
        )

    prompt = build_draft_prompt(bundle, similar_context or [])
    return llm.complete(prompt, system=SYSTEM_PROMPT, temperature=0.5)


def save_draft(
    bundle: Dict,
    draft_md: str,
    drafts_root: Path,
    similar_context: Optional[List[Dict]] = None,
) -> Path:
    """落盘草稿；同时把所用上下文存一份 JSON 旁注便于复盘。"""
    user_id = bundle["user"]["user_id"]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = drafts_root / user_id / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / "draft.md"
    md_path.write_text(draft_md, encoding="utf-8")

    ctx_path = out_dir / "context.json"
    ctx_path.write_text(
        json.dumps(
            {
                "user_id": user_id,
                "username": bundle["user"].get("username"),
                "generated_at": ts,
                "similar_context": similar_context or [],
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return md_path
