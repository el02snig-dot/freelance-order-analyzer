from __future__ import annotations

import json
from typing import Any, Optional

import aiosqlite
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType


class SqliteStorage(BaseStorage):
    """FSM storage backed by SQLite — survives bot restarts."""

    def __init__(self, db_path: str = "fsm.db") -> None:
        self._db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self._db_path)
            await self._db.execute("""
                CREATE TABLE IF NOT EXISTS fsm (
                    key  TEXT PRIMARY KEY,
                    state TEXT,
                    data  TEXT NOT NULL DEFAULT '{}'
                )
            """)
            await self._db.commit()
        return self._db

    @staticmethod
    def _make_key(key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.destiny}"

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        db = await self._get_db()
        state_str = state.state if hasattr(state, "state") else str(state) if state is not None else None
        await db.execute(
            "INSERT INTO fsm (key, state) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET state = excluded.state",
            (self._make_key(key), state_str),
        )
        await db.commit()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        db = await self._get_db()
        async with db.execute(
            "SELECT state FROM fsm WHERE key = ?", (self._make_key(key),)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        db = await self._get_db()
        await db.execute(
            "INSERT INTO fsm (key, data) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET data = excluded.data",
            (self._make_key(key), json.dumps(data, ensure_ascii=False)),
        )
        await db.commit()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        db = await self._get_db()
        async with db.execute(
            "SELECT data FROM fsm WHERE key = ?", (self._make_key(key),)
        ) as cursor:
            row = await cursor.fetchone()
            return json.loads(row[0]) if row and row[0] else {}

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
