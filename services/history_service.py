from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import structlog

logger = structlog.get_logger()

DB_PATH = Path(__file__).parent.parent / "history.db"


class HistoryService:
    @staticmethod
    async def init_db() -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at  TEXT    NOT NULL,
                    user_id     INTEGER NOT NULL,
                    order_text  TEXT    NOT NULL,
                    action      TEXT    NOT NULL,
                    result      TEXT    NOT NULL
                )
            """)
            await db.commit()
        logger.info("history_db_ready", path=str(DB_PATH))

    @staticmethod
    async def save(user_id: int, order_text: str, action: str, result: str) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO history (created_at, user_id, order_text, action, result) VALUES (?, ?, ?, ?, ?)",
                (created_at, user_id, order_text, action, result),
            )
            await db.commit()
        logger.info("history_saved", user_id=user_id, action=action)
