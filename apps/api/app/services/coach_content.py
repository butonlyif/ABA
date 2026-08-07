import sys
from pathlib import Path


def _legacy_root() -> Path:
    legacy = Path("/app/legacy")
    if not legacy.exists():
        legacy = Path(__file__).resolve().parents[4] / "src" / "MVP_web"
    if str(legacy) not in sys.path:
        sys.path.insert(0, str(legacy))
    return legacy


def _content():
    _legacy_root()
    from coach.coach_content import KB_ARTICLES
    return KB_ARTICLES


def _categories_data():
    _legacy_root()
    from coach.coach_content import KB_CATEGORIES
    return KB_CATEGORIES


def articles() -> list[dict]:
    return [
        {"id": key, **{field: item.get(field) for field in ("title", "category", "subcategory", "level", "read_time", "summary")}}
        for key, item in _content().items()
    ]


def search(query: str) -> list[dict]:
    """服务端搜索：标题/摘要/分类/子分类/内容包含 query 即命中。"""
    if not query or not query.strip():
        return []
    q = query.strip()
    hits = []
    for key, item in _content().items():
        haystack = " ".join(str(item.get(field, "")) for field in ("title", "category", "subcategory", "summary", "content"))
        if q in haystack:
            hits.append({"id": key, **{field: item.get(field) for field in ("title", "category", "subcategory", "level", "read_time", "summary")}})
    return hits


def article(article_id: str) -> dict | None:
    item = _content().get(article_id)
    return {"id": article_id, **item} if item else None


def related(article_id: str, limit: int = 3) -> list[dict]:
    """相关文章：优先同子分类，不足时回退到同分类。"""
    item = _content().get(article_id)
    if not item:
        return []
    sub, cat = item.get("subcategory"), item.get("category")
    pool = [(k, v) for k, v in _content().items() if k != article_id]
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
    """分类树：每个 category 含子分类及文章数，过滤掉无文章的子分类。"""
    by_cat: dict[str, list[dict]] = {}
    for item in _content().values():
        by_cat.setdefault(item.get("category", ""), []).append(item)

    def child_articles(cat_id: str, sub_name: str) -> int:
        # 旧平台用子分类名的首段匹配（"焦虑（ anxiety）"→"焦虑"），这里保持一致
        key = sub_name.split("（")[0].split("/")[0].strip()
        return sum(1 for it in by_cat.get(cat_id, []) if key in (it.get("subcategory") or ""))

    result = []
    for cat in _categories_data():
        cat_id = cat["id"]
        if cat_id not in by_cat:
            continue
        children = []
        for ch in cat.get("children", []):
            count = child_articles(cat_id, ch["name"])
            if count > 0:
                children.append({"id": ch["id"], "name": ch["name"], "icon": ch.get("icon", ""), "desc": ch.get("desc", ""), "count": count})
        result.append({
            "id": cat_id, "name": cat["name"], "icon": cat.get("icon", ""),
            "desc": cat.get("desc", ""), "color": cat.get("color", ""),
            "count": len(by_cat[cat_id]), "children": children,
        })
    return result


def issue_stages() -> dict:
    """返回 ISSUE_STAGES_TEMPLATES + TASK_ACTIONS，供前端渲染成长路径。"""
    _legacy_root()
    from coach.coach_content import ISSUE_STAGES_TEMPLATES, TASK_ACTIONS
    # 只返回有 stages 的议题，序列化为纯 dict
    return {"issues": ISSUE_STAGES_TEMPLATES, "task_actions": TASK_ACTIONS}
