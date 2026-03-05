from __future__ import annotations

from typing import Any

from textual import events
from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class VocabCard(Widget):
    """Vocabulary flashcard that flips between German and English.

    Border title shows the topic; border subtitle shows the card index with inline prev/next controls.
    Supports flipping via spacebar or click and emits navigation messages for parent screens.
    """

    BINDINGS = [
        ("space", "flip", "Flip"),
        ("left", "prev_card", "Previous"),
        ("right", "next_card", "Next"),
    ]

    class PrevRequested(Message):
        """Message indicating the previous card was requested."""

    class NextRequested(Message):
        """Message indicating the next card was requested."""

    class CardFlipped(Message):
        """Message indicating the card flip state changed."""

        def __init__(self, showing_english: bool) -> None:
            super().__init__()
            self.showing_english = showing_english

    showing_english: reactive[bool] = reactive(True)

    def __init__(
        self,
        word: dict[str, Any],
        *,
        title: str,
        index: int,
        total: int,
        show_english_first: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.word = word
        self.title = title
        self.index = index
        self.total = total
        self.showing_english = show_english_first

    def compose(self) -> ComposeResult:
        self.border_title = f"{self.title} — Card {self.index + 1}/{self.total}"
        self.border_subtitle = "[@click=prev_card]← Prev[/]  [@click=next_card]Next →[/]"

        german = self.word.get("german") or self.word.get("word") or ""
        english = self.word.get("english") or ""

        with Static(id="vocab-card", classes="vocab-card"):
            yield Static(english, id="card-english", classes="card-face card-english")
            yield Static(german, id="card-german", classes="card-face card-german")

    def on_mount(self) -> None:
        self._update_faces()
        card = self.query_one("#vocab-card", Static)
        card.can_focus = True
        card.focus()

    def on_click(self, event: events.Click) -> None:  # noqa: D401
        self._handle_flip(event)

    def set_card(self, *, word: dict[str, Any], index: int, total: int, title: str | None = None) -> None:
        """Update card content and metadata."""
        self.word = word
        self.index = index
        self.total = total
        if title is not None:
            self.title = title
        self.border_title = f"{self.title} — Card {self.index + 1}/{self.total}"
        self.border_subtitle = "[@click=prev_card]← Prev[/]  [@click=next_card]Next →[/]"

        german = self.word.get("german") or self.word.get("word") or ""
        english = self.word.get("english") or ""
        self.query_one("#card-english", Static).update(english)
        self.query_one("#card-german", Static).update(german)
        self.showing_english = True
        self._update_faces()

    def _update_faces(self) -> None:
        english_face = self.query_one("#card-english", Static)
        german_face = self.query_one("#card-german", Static)

        if self.showing_english:
            english_face.styles.layer = "above"
            english_face.styles.visibility = "visible"
            german_face.styles.layer = "below"
            german_face.styles.visibility = "hidden"
            return

        german_face.styles.layer = "above"
        german_face.styles.visibility = "visible"
        english_face.styles.layer = "below"
        english_face.styles.visibility = "hidden"

    def action_flip(self) -> None:
        self._handle_flip(None)

    def _handle_flip(self, _event) -> None:
        self.showing_english = not self.showing_english
        self._update_faces()
        self.post_message(self.CardFlipped(self.showing_english))

    def action_prev_card(self) -> None:
        self.post_message(self.PrevRequested())

    def action_next_card(self) -> None:
        self.post_message(self.NextRequested())