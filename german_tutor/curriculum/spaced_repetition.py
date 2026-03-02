from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class CardState:
    item_id: str
    ease_factor: float = 2.5
    interval: int = 1  # days until next review
    repetitions: int = 0
    next_review: datetime = field(default_factory=datetime.now)


def calculate_next_review(card: CardState, quality: int) -> CardState:
    """
    Update a card's SM-2 state based on answer quality.

    quality: 0-5
      0 = complete blackout
      1 = incorrect, but familiar
      2 = incorrect, easy to recall
      3 = correct with serious difficulty
      4 = correct with hesitation
      5 = perfect recall

    Returns the mutated card.
    """
    if quality < 3:
        card.repetitions = 0
        card.interval = 1
    else:
        if card.repetitions == 0:
            card.interval = 1
        elif card.repetitions == 1:
            card.interval = 6
        else:
            card.interval = round(card.interval * card.ease_factor)
        card.repetitions += 1

    card.ease_factor = max(
        1.3,
        card.ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02),
    )
    card.next_review = datetime.now() + timedelta(days=card.interval)
    return card


def score_to_quality(score_0_100: int) -> int:
    """
    Map evaluation rubric scores (0/25/50/70/85/100) to SM-2 quality (0-5).

    Rubric:
      100 = perfect            → 5
       85 = minor spelling err → 4
       70 = wrong inflection   → 3
       50 = right word/wrong case → 2
       25 = partial            → 1
        0 = wrong              → 0
    """
    if score_0_100 >= 100:
        return 5
    elif score_0_100 >= 85:
        return 4
    elif score_0_100 >= 70:
        return 3
    elif score_0_100 >= 50:
        return 2
    elif score_0_100 >= 25:
        return 1
    else:
        return 0
