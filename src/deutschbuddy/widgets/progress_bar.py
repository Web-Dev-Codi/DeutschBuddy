from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import ProgressBar, Static


class CEFRProgressBar(Widget):
    """Shows CEFR level progress toward the next level."""

    def __init__(
        self,
        current_level: str,
        next_level: str | None,
        percent: float,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.current_level = current_level
        self.next_level = next_level
        self.percent = percent

    def compose(self) -> ComposeResult:
        label = f"Level: {self.current_level}"
        if self.next_level:
            label += f"  →  {self.next_level}"
        yield Static(label, id="cefr-label", classes="section-header")
        bar = ProgressBar(total=100, show_eta=False)
        bar.advance(self.percent)
        yield bar

    def update_progress(self, percent: float) -> None:
        self.percent = percent
        self.query_one(ProgressBar).update(progress=percent)

    def update_levels(self, current_level: str, next_level: str | None = None) -> None:
        """Update the displayed levels label without remounting the widget."""
        self.current_level = current_level
        self.next_level = next_level
        label = f"Level: {self.current_level}"
        if self.next_level:
            label += f"  →  {self.next_level}"
        self.query_one("#cefr-label", Static).update(label)
