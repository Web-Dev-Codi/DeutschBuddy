from __future__ import annotations

import tomllib
from pathlib import Path

import aiosqlite

_db: aiosqlite.Connection | None = None


def _load_db_path() -> str:
    config_path = Path("config/settings.toml")
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    return config["db"]["path"]


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        db_path = _load_db_path()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(db_path)
        _db.row_factory = aiosqlite.Row
    return _db


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
