import sys
from pathlib import Path


def _content():
    root = Path(__file__).resolve().parents[4]
    legacy = root / "src" / "MVP_web"
    if not legacy.exists():
        legacy = Path("/app/legacy")
    if str(legacy) not in sys.path:
        sys.path.insert(0, str(legacy))
    from coach.coach_content import KB_ARTICLES
    return KB_ARTICLES


def articles() -> list[dict]:
    return [
        {"id": key, **{field: item.get(field) for field in ("title", "category", "subcategory", "level", "read_time", "summary")}}
        for key, item in _content().items()
    ]


def article(article_id: str) -> dict | None:
    item = _content().get(article_id)
    return {"id": article_id, **item} if item else None
