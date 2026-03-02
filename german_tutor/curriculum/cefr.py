from __future__ import annotations

LEVEL_ORDER: list[str] = ["A1", "A2", "B1"]
MASTERY_THRESHOLD: float = 0.75  # 75% avg mastery to advance


class CEFRProgressionEngine:
    """Determines CEFR level advancement based on lesson mastery scores."""

    def can_advance(self, current_level: str, mastery_scores: list[float]) -> bool:
        """
        Returns True if the learner's average mastery score across all lessons
        for the current level meets or exceeds the MASTERY_THRESHOLD.
        """
        if not mastery_scores:
            return False
        avg = sum(mastery_scores) / len(mastery_scores)
        return avg >= MASTERY_THRESHOLD

    def next_level(self, current_level: str) -> str | None:
        """Returns the next CEFR level, or None if already at the top."""
        try:
            idx = LEVEL_ORDER.index(current_level)
        except ValueError:
            return None
        next_idx = idx + 1
        return LEVEL_ORDER[next_idx] if next_idx < len(LEVEL_ORDER) else None

    def progress_percent(self, mastery_scores: list[float]) -> float:
        """
        Returns percentage progress toward the mastery threshold (0-100).
        Capped at 100 even if scores exceed the threshold.
        """
        if not mastery_scores:
            return 0.0
        avg = sum(mastery_scores) / len(mastery_scores)
        return min(100.0, (avg / MASTERY_THRESHOLD) * 100)
