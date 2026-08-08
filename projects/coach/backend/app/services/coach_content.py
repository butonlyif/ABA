"""知识库内容服务：从 markdown 文件加载文章。

读取 projects/coach/knowledge/ 目录下的 .md 文件，解析 YAML frontmatter
与 markdown 正文，构建内存中的文章索引。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from platform_shared.config import get_settings

# 分类元数据（id / 展示名 / 图标），顺序与 INDEX.md 一致
_CATEGORIES = [
    {"id": "methodology", "name": "核心方法论", "icon": "🧠"},
    {"id": "emotion", "name": "情绪与心理管理", "icon": "💬"},
    {"id": "self", "name": "自我认知与成长", "icon": "🌱"},
    {"id": "relationship", "name": "关系经营", "icon": "💑"},
    {"id": "career", "name": "职业与工作", "icon": "💼"},
    {"id": "health", "name": "健康与身心管理", "icon": "🧘"},
    {"id": "habits", "name": "时间与习惯", "icon": "⏰"},
    {"id": "parenting", "name": "养育支持", "icon": "🧒"},
    {"id": "mindfulness", "name": "正念练习库", "icon": "🧘"},
    {"id": "solution-focus", "name": "解决方案聚焦", "icon": "🎯", "desc": "ACT 平复后，用 SF 引导自己从想要的走到一小步",
     "children": [
         {"id": "sf-framework", "name": "框架与流程", "icon": "", "desc": ""},
         {"id": "sf-tools", "name": "核心工具", "icon": "", "desc": ""},
     ]},
]

_FIELDS = ("title", "category", "subcategory", "level", "read_time", "summary")


def _knowledge_root() -> Path:
    settings = get_settings()
    root = Path(settings.knowledge_path)
    if not root.is_absolute():
        candidates = [Path("/app/legacy/knowledge")]
        # 本地开发：从 services/coach_content.py 往上找项目根
        p = Path(__file__).resolve().parent
        for _ in range(5):
            p = p.parent
            candidates.append(p / settings.knowledge_path)
        root = next((c for c in candidates if c.exists()), root)
    return root


def _parse_article(path: Path) -> dict | None:
    """解析单个 .md 文件，返回 {id, title, ...meta, content} 或 None。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    meta = yaml.safe_load(parts[1]) or {}
    content = parts[2].strip()
    article_id = meta.get("id") or path.stem
    return {
        "id": article_id,
        "title": meta.get("title", ""),
        "category": meta.get("category", ""),
        "subcategory": meta.get("subcategory", ""),
        "level": meta.get("level", ""),
        "read_time": meta.get("read_time", ""),
        "summary": meta.get("summary", ""),
        "content": content,
    }


@lru_cache(maxsize=1)
def _load_articles() -> dict[str, dict]:
    """加载全部文章，返回 {id: article_dict}。"""
    root = _knowledge_root()
    articles: dict[str, dict] = {}
    if not root.exists():
        return articles
    for path in sorted(root.rglob("*.md")):
        parsed = _parse_article(path)
        if parsed and parsed["id"]:
            articles[parsed["id"]] = parsed
    return articles


def articles() -> list[dict]:
    return [
        {"id": key, **{field: item.get(field) for field in _FIELDS}}
        for key, item in _load_articles().items()
    ]


def search(query: str) -> list[dict]:
    """服务端搜索：标题/摘要/分类/子分类/内容包含 query 即命中。"""
    if not query or not query.strip():
        return []
    q = query.strip()
    hits = []
    for key, item in _load_articles().items():
        haystack = " ".join(str(item.get(field, "")) for field in (*_FIELDS, "content"))
        if q in haystack:
            hits.append({"id": key, **{field: item.get(field) for field in _FIELDS}})
    return hits


def article(article_id: str) -> dict | None:
    item = _load_articles().get(article_id)
    return {"id": article_id, **item} if item else None


def related(article_id: str, limit: int = 3) -> list[dict]:
    """相关文章：优先同子分类，不足时回退到同分类。"""
    item = _load_articles().get(article_id)
    if not item:
        return []
    sub, cat = item.get("subcategory"), item.get("category")
    pool = [(k, v) for k, v in _load_articles().items() if k != article_id]
    same_sub = [(k, v) for k, v in pool if v.get("subcategory") == sub]
    same_cat = [(k, v) for k, v in pool if v.get("category") == cat]
    picked: list[tuple[str, dict]] = same_sub[:limit]
    if len(picked) < limit:
        exist = {k for k, _ in picked}
        for k, v in same_cat:
            if k not in exist:
                picked.append((k, v))
                if len(picked) >= limit:
                    break
    return [{"id": k, **{f: v.get(f) for f in ("title", "category", "subcategory", "read_time", "summary")}} for k, v in picked]


def categories() -> list[dict]:
    """分类树：每个 category 含子分类及文章数，过滤掉无文章的分类/子分类。"""
    content = _load_articles()
    by_cat: dict[str, list[dict]] = {}
    for item in content.values():
        by_cat.setdefault(item.get("category", ""), []).append(item)

    result = []
    for cat in _CATEGORIES:
        cat_id = cat["id"]
        if cat_id not in by_cat:
            continue
        # 收集该分类下出现的子分类，保持首次出现顺序
        seen: list[str] = []
        for item in by_cat[cat_id]:
            sub = item.get("subcategory")
            if sub and sub not in seen:
                seen.append(sub)
        children = []
        for sub in seen:
            count = sum(1 for it in by_cat[cat_id] if it.get("subcategory") == sub)
            children.append({"id": sub, "name": sub, "icon": "", "desc": "", "count": count})
        result.append({
            "id": cat_id, "name": cat["name"], "icon": cat.get("icon", ""),
            "desc": "", "color": "",
            "count": len(by_cat[cat_id]), "children": children,
        })
    return result


# ─── OSKAR 成长路径（P3）───
_ISSUE_STAGES_TEMPLATES = {
    "困惑": [
        {
            "id": 0, "name": "看清要去哪", "icon": "🔮", "desc": "不分析问题，先描绘你真正想要的画面",
            "guidance": "你希望这一次，带走在什么？不用想怎么解决，先看清楚你想往哪走。",
            "tasks": [
                {"id": "sf1_1", "text": "读：不盯问题", "type": "learn"},
                {"id": "sf1_2", "text": "奇迹问句练习", "type": "practice"},
                {"id": "sf1_3", "text": "写下你想要的画面", "type": "practice"},
            ],
        },
        {
            "id": 1, "name": "给自己定位", "icon": "📏", "desc": "0到10，你现在在哪？为什么不是更低？",
            "guidance": "不给自己打分对错，只是看清现在的位置和已经走过来的那段路。",
            "tasks": [
                {"id": "sf2_1", "text": "读：量尺方法", "type": "learn"},
                {"id": "sf2_2", "text": "打出你的分数", "type": "practice"},
                {"id": "sf2_3", "text": "什么让你到了这个数", "type": "practice"},
            ],
        },
        {
            "id": 2, "name": "找到手里的筹码", "icon": "🃏", "desc": "盘点你已有的资源、技能和曾经「没那么糟」的时刻",
            "guidance": "你其实已经有很多在位的东西，只是平时不会注意到。现在把它们翻出来。",
            "tasks": [
                {"id": "sf3_1", "text": "读：你手里的筹码", "type": "learn"},
                {"id": "sf3_2", "text": "列出3个已有资源", "type": "practice"},
                {"id": "sf3_3", "text": "找出一个「曾经没那么糟」的时刻", "type": "practice"},
            ],
        },
        {
            "id": 3, "name": "选一小步", "icon": "👣", "desc": "上升一分的最小动作，由你选，两分钟内能开始",
            "guidance": "不需要大计划。选一个你能控制、现实可行的最小动作。",
            "tasks": [
                {"id": "sf4_1", "text": "读：一小步原则", "type": "learn"},
                {"id": "sf4_2", "text": "写下你的最小动作", "type": "practice"},
                {"id": "sf4_3", "text": "定下什么时候做", "type": "practice"},
            ],
        },
        {
            "id": 4, "name": "做并观察", "icon": "👀", "desc": "连续几天记录你注意到的变化，哪怕很小",
            "guidance": "每天花一分钟记下：今天我注意到什么不同了？不用评判好坏。",
            "tasks": [
                {"id": "sf5_1", "text": "今日变化记录", "type": "journal"},
                {"id": "sf5_2", "text": "坚持第二天的变化", "type": "journal"},
                {"id": "sf5_3", "text": "坚持第三天的变化", "type": "journal"},
            ],
        },
        {
            "id": 5, "name": "回顾放大", "icon": "🔄", "desc": "什么变好了？你做了什么带来这个改变？",
            "guidance": "回头看看这一路：哪些变化是你自己创造的？什么可以保留、放大？",
            "tasks": [
                {"id": "sf6_1", "text": "读：OSKAR 全流程", "type": "learn"},
                {"id": "sf6_2", "text": "写下什么变好了", "type": "journal"},
                {"id": "sf6_3", "text": "下次想保留什么", "type": "journal"},
            ],
        },
    ],
}

_TASK_ACTIONS = {
    "sf1_1": {"type": "kb", "label": "📖 阅读", "kb_ref": "sf_intro"},
    "sf1_2": {"type": "kb", "label": "📖 阅读", "kb_ref": "sf_future_perfect"},
    "sf1_3": {"type": "journal", "label": "📝 写日记", "prefill_content": "【我想要的是什么】\n假如一夜之间事情好转了一点，明天早上我会先注意到……"},
    "sf2_1": {"type": "kb", "label": "📖 阅读", "kb_ref": "sf_scaling"},
    "sf2_2": {"type": "journal", "label": "📝 写日记", "prefill_content": "【量尺评分】\n0-10 我现在大概在 ____ 分。\n让我到这个分而不是更低的，是……"},
    "sf2_3": {"type": "journal", "label": "📝 写日记", "prefill_content": "【为什么不是更低】\n我已经在做的、帮我维持在现在这个位置的事情是……"},
    "sf3_1": {"type": "kb", "label": "📖 阅读", "kb_ref": "sf_counters"},
    "sf3_2": {"type": "journal", "label": "📝 写日记", "prefill_content": "【我手里的筹码】\n1. \n2. \n3. "},
    "sf3_3": {"type": "journal", "label": "📝 写日记", "prefill_content": "【曾经没那么糟的时刻】\n那一次是……我做了什么让它发生的……"},
    "sf4_1": {"type": "kb", "label": "📖 阅读", "kb_ref": "sf_small_actions"},
    "sf4_2": {"type": "journal", "label": "📝 写日记", "prefill_content": "【我的一小步】\n上升一分的最小动作是……"},
    "sf4_3": {"type": "journal", "label": "📝 写日记", "prefill_content": "【什么时候做】\n我准备在 ____ 做这件事。如果条件不够，我可以缩小为……"},
    "sf5_1": {"type": "journal", "label": "📝 写日记", "prefill_content": "【Day 1 变化记录】\n今天我注意到……"},
    "sf5_2": {"type": "journal", "label": "📝 写日记", "prefill_content": "【Day 2 变化记录】\n坚持第二天，今天的变化是……"},
    "sf5_3": {"type": "journal", "label": "📝 写日记", "prefill_content": "【Day 3 变化记录】\n坚持第三天，今天的变化是……"},
    "sf6_1": {"type": "kb", "label": "📖 阅读", "kb_ref": "sf_oskar"},
    "sf6_2": {"type": "journal", "label": "📝 写日记", "prefill_content": "【什么变好了】\n回顾这一路，我注意到的积极变化是……"},
    "sf6_3": {"type": "journal", "label": "📝 写日记", "prefill_content": "【下次保留什么】\n下次面对类似情境，我学到的最有用的是……"},
}


def issue_stages() -> dict:
    """返回 ISSUE_STAGES_TEMPLATES + TASK_ACTIONS，供前端渲染成长路径。"""
    return {"issues": _ISSUE_STAGES_TEMPLATES, "task_actions": _TASK_ACTIONS}
