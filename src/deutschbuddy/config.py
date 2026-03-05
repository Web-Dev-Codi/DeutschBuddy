# src/deutschbuddy/config.py
from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_config() -> dict:
    """Read config/settings.toml once and cache the result for the process lifetime."""
    with open(Path("config/settings.toml"), "rb") as f:
        return tomllib.load(f)
