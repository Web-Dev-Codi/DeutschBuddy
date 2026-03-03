from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path

import yaml

from german_tutor.models.lesson import Lesson


class CurriculumLoader:
    """Loads lesson definitions from YAML files on disk.

    Results are cached in memory after first load — subsequent calls are O(1).
    """

    def __init__(self, data_path: str = "data/curriculum") -> None:
        self.base_path = Path(data_path)
        self._cache: dict[str, list[Lesson]] = {}
        self._lesson_cache: dict[str, Lesson] = {}

    # ── Synchronous helpers (called from asyncio.to_thread) ──────────────────

    def _load_lesson_sync(self, file_path: Path) -> Lesson:
        try:
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return Lesson(**data)
        except Exception as exc:
            raise ValueError(f"Failed to load lesson from {file_path}: {exc}") from exc

    def _load_level_sync(self, level: str) -> list[Lesson]:
        level_path = self.base_path / level
        if not level_path.exists():
            return []
        return [self._load_lesson_sync(p) for p in sorted(level_path.glob("*.yaml"))]

    def _load_all_sync(self) -> dict[str, list[Lesson]]:
        return {level: self._load_level_sync(level) for level in ["A1", "A2", "B1"]}

    # ── Public synchronous API (cache-backed after first load) ───────────────

    def load_lesson(self, file_path: Path) -> Lesson:
        file_path_str = str(file_path)
        if file_path_str not in self._lesson_cache:
            self._lesson_cache[file_path_str] = self._load_lesson_sync(file_path)
        return self._lesson_cache[file_path_str]

    def load_level(self, level: str) -> list[Lesson]:
        if level in self._cache:
            return self._cache[level]
        lessons = self._load_level_sync(level)
        self._cache[level] = lessons
        return lessons

    def load_all(self) -> dict[str, list[Lesson]]:
        if self._cache and all(level in self._cache for level in ["A1", "A2", "B1"]):
            return self._cache
        result = self._load_all_sync()
        self._cache.update(result)
        return result

    # ── Public async API ─────────────────────────────────────────────────────

    async def load_all_async(self) -> dict[str, list[Lesson]]:
        """Load all lessons off the event loop, caching the result."""
        if self._cache and all(level in self._cache for level in ["A1", "A2", "B1"]):
            return self._cache
        result = await asyncio.to_thread(self._load_all_sync)
        self._cache.update(result)
        return result

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get_lesson_by_id(self, lesson_id: str) -> Lesson | None:
        for lessons in self.load_all().values():
            for lesson in lessons:
                if lesson.id == lesson_id:
                    return lesson
        return None

    def get_lessons_by_ids(self, lesson_ids: list[str]) -> list[Lesson]:
        """Get multiple lessons by their IDs. Returns empty list for unknown IDs."""
        if not lesson_ids:
            return []

        all_lessons = []
        for lessons in self.load_all().values():
            all_lessons.extend(lessons)

        # Create a dict for O(1) lookup
        lesson_dict = {lesson.id: lesson for lesson in all_lessons}

        # Return lessons in the order requested, filtering out unknown IDs
        return [
            lesson_dict[lesson_id]
            for lesson_id in lesson_ids
            if lesson_id in lesson_dict
        ]
