"""Tests for CurriculumLoader caching strategies."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml

from deutschbuddy.curriculum.loader import CurriculumLoader
from deutschbuddy.models.lesson import Lesson


class TestCurriculumLoaderLazyLoading:
    """Test that levels are loaded on-demand, not all at startup."""

    def test_cache_empty_on_init(self):
        """Loader should start with empty cache, not None."""
        loader = CurriculumLoader()
        assert loader._cache == {}

    def test_load_level_caches_individually(self, tmp_path):
        """Loading one level should only cache that level."""
        level_path = tmp_path / "A1"
        level_path.mkdir()
        lesson_file = level_path / "test_lesson.yaml"
        lesson_file.write_text("""id: test_1
level: A1
category: grammar
title: Test Lesson
estimated_minutes: 10
explanation:
  concept: Test concept
""")

        loader = CurriculumLoader(data_path=str(tmp_path))

        lessons = loader.load_level("A1")

        assert len(lessons) == 1
        assert loader._cache["A1"] is not None
        assert "A2" not in loader._cache
        assert "B1" not in loader._cache

    def test_load_all_populates_all_levels(self, tmp_path):
        """load_all should populate cache with all levels."""
        for level in ["A1", "A2", "B1"]:
            level_path = tmp_path / level
            level_path.mkdir()
            lesson_file = level_path / f"{level.lower()}_lesson.yaml"
            lesson_file.write_text(f"""id: {level.lower()}_1
level: {level}
category: grammar
title: {level} Lesson
estimated_minutes: 10
explanation:
  concept: Test concept
""")

        loader = CurriculumLoader(data_path=str(tmp_path))
        result = loader.load_all()

        assert "A1" in loader._cache
        assert "A2" in loader._cache
        assert "B1" in loader._cache


class TestLRUCachePerLesson:
    """Test that individual lessons are cached using LRU cache."""

    def test_same_lesson_returns_cached(self, tmp_path):
        """Loading same lesson twice should use cache."""
        level_path = tmp_path / "A1"
        level_path.mkdir()
        lesson_file = level_path / "test_lesson.yaml"
        lesson_file.write_text("""id: test_1
level: A1
category: grammar
title: Test Lesson
estimated_minutes: 10
explanation:
  concept: Test concept
""")

        loader = CurriculumLoader(data_path=str(tmp_path))

        lesson1 = loader.load_lesson(lesson_file)
        lesson2 = loader.load_lesson(lesson_file)

        assert lesson1 is lesson2
        assert lesson1.id == "test_1"

    def test_different_lessons_loaded_separately(self, tmp_path):
        """Different lessons should be cached separately."""
        level_path = tmp_path / "A1"
        level_path.mkdir()

        lesson1_file = level_path / "lesson1.yaml"
        lesson1_file.write_text("""id: lesson1
level: A1
category: grammar
title: Lesson 1
estimated_minutes: 10
explanation:
  concept: Test concept 1
""")

        lesson2_file = level_path / "lesson2.yaml"
        lesson2_file.write_text("""id: lesson2
level: A1
category: grammar
title: Lesson 2
estimated_minutes: 10
explanation:
  concept: Test concept 2
""")

        loader = CurriculumLoader(data_path=str(tmp_path))

        lesson1 = loader.load_lesson(lesson1_file)
        lesson2 = loader.load_lesson(lesson2_file)

        assert lesson1.id == "lesson1"
        assert lesson2.id == "lesson2"
        assert lesson1 is not lesson2
