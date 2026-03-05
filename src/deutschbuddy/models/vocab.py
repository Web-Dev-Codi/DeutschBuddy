from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel

from deutschbuddy.models.lesson import CEFRLevel


class VocabWord(BaseModel):
    german: str
    english: str


class VocabTopic(BaseModel):
    id: str
    title: str
    level: CEFRLevel
    words: List[VocabWord]


class VocabTopicProgress(BaseModel):
    id: int | None = None
    learner_id: int
    topic_id: str
    topic_level: CEFRLevel
    total_words: int
    words_seen: int = 0
    completed_percent: float = 0.0
    last_interacted_at: datetime | None = None
