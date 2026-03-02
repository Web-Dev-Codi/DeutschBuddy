from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Learner(BaseModel):
    id: Optional[int] = None
    name: str
    current_level: str = "A1"
    created_at: Optional[datetime] = None
    streak_days: int = 0
    last_session_date: Optional[datetime] = None
