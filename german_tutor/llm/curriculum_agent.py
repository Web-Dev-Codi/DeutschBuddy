from __future__ import annotations

import json

from german_tutor.llm.client import OllamaClient
from german_tutor.llm.prompts import PROMPTS
from german_tutor.models.learner import Learner
from german_tutor.models.lesson import (
    CEFRLevel,
    Lesson,
    LessonProgress,
    LessonRecommendation,
)


class CurriculumAgent:
    """Decides which lesson to teach next and analyses post-session performance."""

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.model = client.curriculum_model

    async def recommend_next_lesson(
        self,
        learner: Learner,
        performance_history: list[dict],
        available_lessons: list[Lesson],
        due_reviews: list[LessonProgress],
    ) -> LessonRecommendation:
        """Ask the LLM to recommend the next lesson based on learner state."""
        from datetime import date

        template = PROMPTS["curriculum"]
        messages = [
            {"role": "system", "content": template.system},
            {
                "role": "user",
                "content": template.render_user(
                    learner_name=learner.name,
                    current_level=learner.current_level.value,
                    total_completed=str(len(performance_history)),
                    streak_days=str(learner.streak_days),
                    performance_history_json=json.dumps(performance_history, indent=2),
                    due_reviews_json=json.dumps(
                        [
                            {"lesson_id": r.lesson_id, "mastery_score": r.mastery_score}
                            for r in due_reviews
                        ],
                        indent=2,
                    ),
                    available_lessons_json=json.dumps(
                        [
                            {
                                "id": l.id,
                                "title": l.title,
                                "category": l.category.value,
                                "prerequisites": l.prerequisites,
                            }
                            for l in available_lessons
                        ],
                        indent=2,
                    ),
                    today_date=str(date.today()),
                ),
            },
        ]
        result = await self.client.chat_json(model=self.model, messages=messages)
        return LessonRecommendation(**result)

    async def generate_performance_analysis(
        self,
        learner: Learner,
        session_results: dict,
        question_breakdown: list[dict],
        history: list[dict],
    ) -> dict:
        """Generate a coaching report after a quiz session."""
        template = PROMPTS["analysis"]
        messages = [
            {"role": "system", "content": template.system},
            {
                "role": "user",
                "content": template.render_user(
                    learner_name=learner.name,
                    cefr_level=learner.current_level.value,
                    lesson_title=session_results.get("lesson_title", ""),
                    session_results_json=json.dumps(session_results, indent=2),
                    question_breakdown_json=json.dumps(question_breakdown, indent=2),
                    history_json=json.dumps(history, indent=2),
                ),
            },
        ]
        return await self.client.chat_json(model=self.model, messages=messages)
