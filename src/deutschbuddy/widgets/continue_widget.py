from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static


class ContinueLessonWidget(Widget):
    """Clickable card to continue current lesson or open lessons list."""

    BINDINGS = [
        ("enter", "activate", "Open"),
        ("space", "activate", "Open"),
    ]

    class OpenRequested(Message):
        """Emitted when the widget is activated to open or continue lesson."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._lesson_id: str | None = None
        self._title: str | None = None
        self._level: str | None = None
        self._minutes: int | None = None

    def compose(self) -> ComposeResult:
        yield Static("Continue Lesson", classes="home-widget-title")
        self._line_id = Static("Choose your next lesson", classes="home-widget-row")
        self._line_title = Static("", classes="home-widget-row")
        self._line_meta = Static("", classes="home-widget-row")
        self._affordance = Static("Open lessons", classes="home-widget-affordance")
        yield self._line_id
        yield self._line_title
        yield self._line_meta
        yield self._affordance

    def on_mount(self) -> None:
        self.can_focus = True

    def on_click(self, _event: events.Click) -> None:
        self.post_message(self.OpenRequested())

    def action_activate(self) -> None:
        self.post_message(self.OpenRequested())

    def set_lesson(
        self,
        *,
        lesson_id: str | None,
        title: str | None,
        level: str | None,
        minutes: int | None,
    ) -> None:
        self._lesson_id = lesson_id
        self._title = title
        self._level = level
        self._minutes = minutes

        if lesson_id and title and level and minutes is not None:
            self._line_id.update(str(lesson_id))
            self._line_title.update(str(title))
            self._line_meta.update(f"{level} \u00B7 {minutes} min")
            self._affordance.update("Open lesson")
            return

        self._line_id.update("Choose your next lesson")
        self._line_title.update("")
        self._line_meta.update("")
        self._affordance.update("Open lessons")
