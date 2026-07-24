import os
import sys
from pathlib import Path


def _module():
    root = Path(__file__).resolve().parents[4]
    legacy = root / "src" / "MVP_web"
    if not legacy.exists():
        legacy = Path("/app/legacy")
    if str(legacy) not in sys.path:
        sys.path.insert(0, str(legacy))
    from training import flashcards
    asset_root = os.getenv("ABA_FLASHCARD_ASSET_ROOT")
    if asset_root:
        flashcards.ABA_IMAGES_DIR = str(Path(asset_root) / "图片")
        flashcards.IMAGE_CARDS_DIR = str(Path(asset_root) / "图片卡_网络素材")
    return flashcards


def catalog() -> list[dict]:
    flashcards = _module()
    items = []
    for group, categories in flashcards.get_grouped_categories().items():
        items.append({
            "group": group,
            "categories": [
                {"name": category, "count": flashcards.get_page_count(category)}
                for category in categories
            ],
        })
    return items


def card(category: str, index: int) -> tuple[bytes | None, str]:
    flashcards = _module()
    data = flashcards.render_page_as_png_bytes(category, index)
    label = flashcards.get_card_label(category, index)
    return data, label
