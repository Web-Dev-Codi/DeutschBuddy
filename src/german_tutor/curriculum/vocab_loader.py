from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from german_tutor.models.lesson import CEFRLevel
from german_tutor.models.vocab import VocabTopic, VocabWord


class VocabLoader:
    """Loads vocabulary topics from YAML files.

    Expects files named by level, e.g. data/vocab/a1.yml with structure:
    topics:
      - id: greetings
        title: Greetings & Farewells
        level: A1
        words:
          - german: "Hallo"
            english: "Hello"
    """

    def __init__(self, data_path: str = "data/vocab") -> None:
        self.base_path = Path(data_path)
        self._cache: dict[str, List[VocabTopic]] = {}

    def _load_level_sync(self, level: str) -> List[VocabTopic]:
        file_path = self.base_path / f"{level.lower()}.yml"
        if not file_path.exists():
            return []
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        topics_raw = data.get("topics", [])
        topics: List[VocabTopic] = []
        for item in topics_raw:
            words = [VocabWord(**w) for w in item.get("words", [])]
            topic_level = item.get("level", level)
            topics.append(
                VocabTopic(
                    id=item["id"],
                    title=item.get("title", item["id"].replace("-", " ")),
                    level=CEFRLevel(topic_level),
                    words=words,
                )
            )
        return topics

    def load_level(self, level: str) -> List[VocabTopic]:
        if level in self._cache:
            return self._cache[level]
        topics = self._load_level_sync(level)
        self._cache[level] = topics
        return topics

    def load_all(self) -> dict[str, List[VocabTopic]]:
        result: dict[str, List[VocabTopic]] = {}
        for level in ["A1", "A2", "B1"]:
            result[level] = self.load_level(level)
        return result

    def get_topic(self, level: str, topic_id: str) -> VocabTopic | None:
        for topic in self.load_level(level):
            if topic.id == topic_id:
                return topic
        return None

    def get_topics_by_ids(self, level: str, topic_ids: list[str]) -> list[VocabTopic]:
        if not topic_ids:
            return []
        level_topics = {topic.id: topic for topic in self.load_level(level)}
        return [level_topics[tid] for tid in topic_ids if tid in level_topics]
