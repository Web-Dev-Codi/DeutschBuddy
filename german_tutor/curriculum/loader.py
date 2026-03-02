from __future__ import annotations

from pathlib import Path

import yaml

from german_tutor.models.lesson import Lesson


class CurriculumLoader:
    """Loads lesson definitions from YAML files on disk."""

    def __init__(self, data_path: str = "data/curriculum") -> None:
        self.base_path = Path(data_path)

    def load_lesson(self, file_path: Path) -> Lesson:
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return Lesson(**data)

    def load_level(self, level: str) -> list[Lesson]:
        """Load all lessons for a CEFR level, sorted by filename."""
        level_path = self.base_path / level
        if not level_path.exists():
            return []
        lessons = []
        for yaml_file in sorted(level_path.glob("*.yaml")):
            lessons.append(self.load_lesson(yaml_file))
        return lessons

    def load_all(self) -> dict[str, list[Lesson]]:
        """Load all available CEFR levels."""
        return {level: self.load_level(level) for level in ["A1", "A2", "B1"]}

    def get_lesson_by_id(self, lesson_id: str) -> Lesson | None:
        """Find a lesson by its ID across all levels."""
        for lessons in self.load_all().values():
            for lesson in lessons:
                if lesson.id == lesson_id:
                    return lesson
        return None
