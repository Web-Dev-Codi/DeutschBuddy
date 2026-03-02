from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, LoadingIndicator, Static

from german_tutor.models.learner import Learner
from german_tutor.models.lesson import Lesson
from german_tutor.widgets.grammar_panel import GrammarPanelWidget
from german_tutor.widgets.sentence_tree import SentenceBreakdownWidget


class LessonScreen(Screen):
    """Displays a lesson with AI grammar explanation and sentence breakdowns."""

    BINDINGS = [("escape", "go_back", "Back"), ("q", "start_quiz", "Quiz")]

    def __init__(
        self,
        lesson: Lesson,
        learner: Learner,
        tutor_agent=None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.lesson = lesson
        self.learner = learner
        self.tutor_agent = tutor_agent
        self._explanation: dict | None = None
        self._breakdowns: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Static(id="main-content"):
            yield Static(
                f"{self.lesson.id} — {self.lesson.title}",
                classes="section-header",
            )
            yield Static(
                f"Level: {self.lesson.level.value}  |  "
                f"Category: {self.lesson.category.value}  |  "
                f"~{self.lesson.estimated_minutes} min",
                classes="quiz-context",
            )

            if self._explanation:
                yield GrammarPanelWidget(self._explanation, id="grammar-panel")
            else:
                yield Static(
                    "Loading AI explanation...", id="grammar-loading", classes="loading"
                )

            yield Static("Example Sentences", classes="section-header")
            for i, sent in enumerate(self.lesson.example_sentences[:3]):
                yield Static(
                    f"DE: {sent.get('german', '')}  |  EN: {sent.get('english', '')}",
                    classes="german-sentence",
                    id=f"sentence-{i}",
                )

            with Static(classes="action-buttons"):
                yield Button("Start Quiz", id="btn-quiz", variant="primary")
                yield Button("Back", id="btn-back", variant="default")

        yield Footer()

    async def on_mount(self) -> None:
        """Load AI explanation asynchronously after the screen mounts."""
        if self.tutor_agent is not None:
            try:
                self._explanation = await self.tutor_agent.explain_lesson(
                    self.lesson, self.learner
                )
                # Replace loading indicator with actual explanation
                try:
                    self.query_one("#grammar-loading").remove()
                except Exception:
                    pass
                await self.mount(
                    GrammarPanelWidget(self._explanation, id="grammar-panel"),
                    after=self.query_one("#main-content").children[2],
                )
            except Exception as exc:
                try:
                    self.query_one("#grammar-loading", Static).update(
                        f"Could not load explanation: {exc}"
                    )
                except Exception:
                    pass

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_start_quiz(self) -> None:
        from german_tutor.screens.home import NavRequest

        self.app.post_message(NavRequest("quiz"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.action_go_back()
        elif event.button.id == "btn-quiz":
            self.action_start_quiz()
