from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel


class CEFRLevel(str, Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"


class LessonCategory(str, Enum):
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    SENTENCE_STRUCTURE = "sentence_structure"


class QuizQuestion(BaseModel):
    type: Literal["multiple_choice", "fill_blank", "translation", "reorder"]
    question: str
    context: Optional[str] = None
    options: Optional[list[str]] = None
    correct_answer: str
    correct_answer_index: Optional[int] = None
    answer_explanation: str
    grammar_rule_tested: str
    english_comparison: str
    hint: str
    points: int = 10


class LessonQuiz(BaseModel):
    questions: list[QuizQuestion]


class Lesson(BaseModel):
    id: str  # e.g. "A1-GRM-002"
    level: CEFRLevel
    category: LessonCategory
    title: str
    prerequisites: list[str] = []
    estimated_minutes: int
    tags: list[str] = []
    fundamentals: Optional[dict] = None
    explanation: dict
    example_sentences: list[dict] = []
    quiz: Optional[LessonQuiz] = None


class LessonRecommendation(BaseModel):
    recommended_lesson_id: str
    lesson_title: str
    reason: str
    difficulty_adjustment: str
    english_speaker_warning: Optional[str] = None
    estimated_minutes: int
    review_items: list[str] = []


class LessonProgress(BaseModel):
    id: Optional[int] = None
    learner_id: int
    lesson_id: str
    completed_at: Optional[datetime] = None
    attempts: int = 0
    last_score: float = 0.0
    mastery_score: float = 0.0
    next_review: Optional[datetime] = None
    ease_factor: float = 2.5
