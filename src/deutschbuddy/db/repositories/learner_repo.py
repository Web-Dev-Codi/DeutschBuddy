from __future__ import annotations

from datetime import datetime

import aiosqlite

from german_tutor.models.learner import Learner
from german_tutor.models.lesson import CEFRLevel


class LearnerRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(self, name: str) -> Learner:
        async with self.db.execute(
            "INSERT INTO learner (name) VALUES (?) RETURNING id, name, current_level, streak_days, last_session_date, created_at, daily_goal_minutes, last_lesson_id",
            (name,),
        ) as cursor:
            row = await cursor.fetchone()
        await self.db.commit()
        return self._row_to_learner(row)

    async def get_by_id(self, learner_id: int) -> Learner | None:
        async with self.db.execute(
            "SELECT id, name, current_level, streak_days, last_session_date, created_at, daily_goal_minutes, last_lesson_id FROM learner WHERE id = ?",
            (learner_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return self._row_to_learner(row) if row else None

    async def get_first(self) -> Learner | None:
        async with self.db.execute(
            "SELECT id, name, current_level, streak_days, last_session_date, created_at, daily_goal_minutes, last_lesson_id FROM learner LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
        return self._row_to_learner(row) if row else None

    async def update_level(self, learner_id: int, level: CEFRLevel) -> None:
        await self.db.execute(
            "UPDATE learner SET current_level = ? WHERE id = ?",
            (level.value, learner_id),
        )
        await self.db.commit()

    async def update_streak(
        self, learner_id: int, streak: int, last_date: datetime
    ) -> None:
        await self.db.execute(
            "UPDATE learner SET streak_days = ?, last_session_date = ? WHERE id = ?",
            (streak, last_date.isoformat(), learner_id),
        )
        await self.db.commit()

    async def update_goal(self, learner_id: int, daily_goal_minutes: int) -> None:
        """Update the learner's daily goal in minutes."""
        await self.db.execute(
            "UPDATE learner SET daily_goal_minutes = ? WHERE id = ?",
            (daily_goal_minutes, learner_id),
        )
        await self.db.commit()

    async def update_last_lesson(self, learner_id: int, lesson_id: str) -> None:
        """Update the learner's last lesson ID."""
        await self.db.execute(
            "UPDATE learner SET last_lesson_id = ? WHERE id = ?",
            (lesson_id, learner_id),
        )
        await self.db.commit()

    def _row_to_learner(self, row: aiosqlite.Row) -> Learner:
        d = dict(row)
        d["current_level"] = CEFRLevel(d["current_level"])
        return Learner(**d)
