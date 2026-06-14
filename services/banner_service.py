from __future__ import annotations

import random
from pathlib import Path

BANNERS_DIR = Path(__file__).parent.parent / "banners"


def get_random_banner(category: str, subcategory: str, subtype: str = "") -> Path | None:
    folder = BANNERS_DIR / category / subcategory
    if subtype:
        folder = folder / subtype
    if not folder.exists():
        return None
    banners = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg")]
    if not banners:
        return None
    return random.choice(banners)
