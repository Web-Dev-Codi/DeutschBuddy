from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class StatsWidget(Widget):
    """Compact stats widget for Today, Lessons, and Vocab."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._minutes_today: float = 0.0
        self._lessons_completed: int = 0
        self._lessons_total: int = 0
        self._vocab_count: int = 0

    def compose(self) -> ComposeResult:
        yield Static("", classes="home-widget-title")
        self._today_label = Static("Today", classes="home-widget-row")
        self._today_value = Static("0 min", classes="home-widget-row")
        self._lessons_label = Static("Lessons", classes="home-widget-row")
        self._lessons_value = Static("0/0", classes="home-widget-row")
        self._vocab_label = Static("Vocab", classes="home-widget-row")
        self._vocab_value = Static("0 words", classes="home-widget-row")
        self.border_title = "Stats"
        self.border_subtitle = "Today, Lessons, and Vocab"
        yield self._today_label
        yield self._today_value
        yield self._lessons_label
        yield self._lessons_value
        yield self._vocab_label
        yield self._vocab_value

    def set_stats(
        self,
        *,
        minutes_today: float,
        lessons_completed: int,
        lessons_total: int,
        vocab_count: int,
    ) -> None:
        self._minutes_today = minutes_today
        self._lessons_completed = lessons_completed
        self._lessons_total = lessons_total
        self._vocab_count = vocab_count

        if hasattr(self, "_today_value"):
            self._today_value.update(f"{minutes_today:.0f} min")
            self._lessons_value.update(f"{lessons_completed}/{lessons_total}")
            self._vocab_value.update(f"{vocab_count} words")
