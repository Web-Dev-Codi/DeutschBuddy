from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from german_tutor.widgets.sentence_tree import SentenceBreakdownWidget


class BreakdownScreen(Screen):
    """Full-page sentence analysis view showing word-by-word grammatical breakdown."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(
        self,
        sentence: str,
        cefr_level: str,
        tutor_agent=None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.sentence = sentence
        self.cefr_level = cefr_level
        self.tutor_agent = tutor_agent
        self._breakdown: dict | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Static(id="main-content"):
            yield Static("Sentence Breakdown", classes="section-header")
            yield Static(self.sentence, classes="german-sentence")
            yield Static(
                "Analysing sentence...", id="breakdown-loading", classes="loading"
            )
            with Static(classes="action-buttons"):
                yield Button("Back", id="btn-back", variant="default")
        yield Footer()

    async def on_mount(self) -> None:
        if self.tutor_agent is not None:
            try:
                self._breakdown = await self.tutor_agent.breakdown_sentence(
                    self.sentence, self.cefr_level
                )
                self.query_one("#breakdown-loading").remove()
                await self.mount(
                    SentenceBreakdownWidget(self._breakdown),
                    after=self.query_one("#main-content").children[1],
                )
            except Exception as exc:
                self.query_one("#breakdown-loading", Static).update(
                    f"Could not analyse sentence: {exc}"
                )

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.action_go_back()
