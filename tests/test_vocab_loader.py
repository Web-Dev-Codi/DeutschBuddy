import yaml
from pathlib import Path

from deutschbuddy.curriculum.vocab_loader import VocabLoader
from deutschbuddy.models.lesson import CEFRLevel


def test_load_level_parses_topics(tmp_path: Path):
    data_dir = tmp_path / "vocab"
    data_dir.mkdir()
    sample = {
        "topics": [
            {
                "id": "greetings",
                "title": "Greetings",
                "level": "A1",
                "words": [
                    {"german": "Hallo", "english": "Hello"},
                    {"german": "Tschüss", "english": "Bye"},
                ],
            }
        ]
    }
    (data_dir / "a1.yml").write_text(yaml.safe_dump(sample), encoding="utf-8")

    loader = VocabLoader(data_path=str(data_dir))

    topics = loader.load_level("A1")

    assert len(topics) == 1
    topic = topics[0]
    assert topic.id == "greetings"
    assert topic.title == "Greetings"
    assert topic.level == CEFRLevel.A1
    assert len(topic.words) == 2
    assert topic.words[0].german == "Hallo"
    # Second call should hit cache
    again = loader.load_level("A1")
    assert topics is again
