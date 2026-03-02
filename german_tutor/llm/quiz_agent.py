from __future__ import annotations

import json

from german_tutor.llm.client import OllamaClient
from german_tutor.llm.prompts import PROMPTS
from german_tutor.models.learner import Learner
from german_tutor.models.lesson import Lesson


class QuizAgent:
    """Generates quiz questions, evaluates answers, and provides progressive hints."""

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.model = client.interaction_model

    async def generate_quiz(self, lesson: Lesson, learner: Learner) -> dict:
        """Generate a 10-question quiz for the given lesson."""
        vocab_list = [s.get("german", "") for s in lesson.example_sentences]

        template = PROMPTS["quiz_gen"]
        messages = [
            {"role": "system", "content": template.system},
            {
                "role": "user",
                "content": template.render_user(
                    lesson_id=lesson.id,
                    lesson_title=lesson.title,
                    cefr_level=learner.current_level.value,
                    concept_description=lesson.explanation.get("concept", ""),
                    vocabulary_list=json.dumps(vocab_list),
                    weak_areas="None identified yet",
                ),
            },
        ]
        return await self.client.chat_json(model=self.model, messages=messages)

    async def evaluate_answer(
        self,
        question: str,
        user_answer: str,
        correct_answer: str,
        grammar_rule: str,
        cefr_level: str,
    ) -> dict:
        """Grade a free-form learner answer and return feedback."""
        template = PROMPTS["evaluation"]
        messages = [
            {"role": "system", "content": template.system},
            {
                "role": "user",
                "content": template.render_user(
                    cefr_level=cefr_level,
                    question=question,
                    correct_answer=correct_answer,
                    user_answer=user_answer,
                    grammar_rule=grammar_rule,
                ),
            },
        ]
        return await self.client.chat_json(model=self.model, messages=messages)

    async def get_hint(
        self,
        question: str,
        correct_answer: str,
        grammar_rule: str,
        hint_level: int,
        attempted_answer: str = "",
    ) -> dict:
        """Get a progressive hint (level 1-3) without revealing the answer."""
        template = PROMPTS["hint"]
        messages = [
            {"role": "system", "content": template.system},
            {
                "role": "user",
                "content": template.render_user(
                    question=question,
                    correct_answer=correct_answer,
                    grammar_rule=grammar_rule,
                    hint_level=str(hint_level),
                    attempted_answer=attempted_answer,
                ),
            },
        ]
        return await self.client.chat_json(model=self.model, messages=messages)
