from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_SKILLSET_PATH = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "skills"
    / "analyze"
    / "skillset-zerocoder.md"
)


@lru_cache(maxsize=1)
def load_skillset() -> str:
    if not _SKILLSET_PATH.exists():
        return "Скиллсет не найден."
    return _SKILLSET_PATH.read_text(encoding="utf-8")
