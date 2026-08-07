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
