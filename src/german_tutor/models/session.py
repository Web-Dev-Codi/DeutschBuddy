from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class QuizResponse(BaseModel):
    id: Optional[int] = None
    session_id: Optional[int] = None
    question_id: str
    user_answer: str
    is_correct: bool
    time_taken_seconds: int = 0
    llm_evaluation: Optional[dict] = None


class QuizSession(BaseModel):
    id: Optional[int] = None
    learner_id: int
    lesson_id: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_questions: int = 0
    correct_answers: int = 0
    score: float = 0.0
    llm_feedback: Optional[dict] = None
    responses: list[QuizResponse] = []
