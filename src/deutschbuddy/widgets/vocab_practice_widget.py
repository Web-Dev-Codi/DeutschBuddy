from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static


class VocabPracticeWidget(Widget):
    """Clickable card previewing the next vocab word to practice."""

    BINDINGS = [
        ("enter", "activate", "Open"),
        ("space", "activate", "Open"),
    ]

    class OpenRequested(Message):
        """Emitted when the widget is activated to open practice."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._german: str | None = None
        self._topic_title: str | None = None

    def compose(self) -> ComposeResult:
        yield Static("Practice Vocabulary", classes="home-widget-title")
        self._word_line = Static("Start vocab practice", classes="home-widget-row")
        self._topic_line = Static("", classes="home-widget-row")
        self._affordance = Static("Open practice", classes="home-widget-affordance")
        yield self._word_line
        yield self._topic_line
        yield self._affordance

    def on_mount(self) -> None:
        container = self
        container.can_focus = True

    def on_click(self, _event: events.Click) -> None:
        self.post_message(self.OpenRequested())

    def action_activate(self) -> None:
        self.post_message(self.OpenRequested())

    def set_preview(self, *, german: str | None, topic_title: str | None) -> None:
        self._german = german
        self._topic_title = topic_title
        if german and topic_title:
            self._word_line.update(german)
            self._topic_line.update(topic_title)
        else:
            self._word_line.update("Start vocab practice")
            self._topic_line.update("")
