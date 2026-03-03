from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class StreakIndicator(Widget):
    """Displays the learner's current daily streak."""

    def __init__(self, streak_days: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.streak_days = streak_days

    def compose(self) -> ComposeResult:
        if self.streak_days == 0:
            text = "Start your streak today!"
        elif self.streak_days == 1:
            text = "Streak: 1 day"
        else:
            text = f"Streak: {self.streak_days} days"
        yield Static(text)

    def update_streak(self, days: int) -> None:
        self.streak_days = days
        if days == 0:
            text = "Start your streak today!"
        elif days == 1:
            text = "Streak: 1 day"
        else:
            text = f"Streak: {days} days"
        self.query_one(Static).update(text)
