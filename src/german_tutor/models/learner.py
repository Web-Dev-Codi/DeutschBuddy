from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from german_tutor.models.lesson import CEFRLevel


class Learner(BaseModel):
    id: Optional[int] = None
    name: str
    current_level: CEFRLevel = CEFRLevel.A1
    created_at: Optional[datetime] = None
    streak_days: int = 0
    last_session_date: Optional[datetime] = None
    daily_goal_minutes: int = 20
    last_lesson_id: Optional[str] = None
