from __future__ import annotations

from german_tutor.llm.client import OllamaClient
from german_tutor.llm.prompts import PROMPTS
from german_tutor.models.learner import Learner
from german_tutor.models.lesson import Lesson


class TutorAgent:
    """Generates grammar explanations, sentence breakdowns, and vocabulary entries."""

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.model = client.interaction_model

    async def explain_lesson(self, lesson: Lesson, learner: Learner) -> dict:
        """Generate an AI grammar explanation for a lesson."""
        template = PROMPTS["tutor"]
        messages = [
            {"role": "system", "content": template.system},
            {
                "role": "user",
                "content": template.render_user(
                    lesson_title=lesson.title,
                    cefr_level=learner.current_level.value,
                    concept_description=lesson.explanation.get("concept", ""),
                    weak_areas="None identified yet",
                ),
            },
        ]
        return await self.client.chat_json(model=self.model, messages=messages)

    async def breakdown_sentence(self, sentence: str, cefr_level: str) -> dict:
        """Produce a word-by-word grammatical breakdown of a German sentence."""
        template = PROMPTS["breakdown"]
        messages = [
            {"role": "system", "content": template.system},
            {
                "role": "user",
                "content": template.render_user(
                    cefr_level=cefr_level,
                    german_sentence=sentence,
                ),
            },
        ]
        return await self.client.chat_json(model=self.model, messages=messages)

    async def get_vocabulary_entry(self, german_word: str, cefr_level: str) -> dict:
        """Generate a full vocabulary entry with examples and memory tips."""
        template = PROMPTS["vocabulary"]
        messages = [
            {"role": "system", "content": template.system},
            {
                "role": "user",
                "content": template.render_user(
                    german_word=german_word,
                    cefr_level=cefr_level,
                ),
            },
        ]
        return await self.client.chat_json(model=self.model, messages=messages)
