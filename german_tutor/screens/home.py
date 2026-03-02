from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

from german_tutor.models.learner import Learner
from german_tutor.models.lesson import LessonRecommendation
from german_tutor.widgets.progress_bar import CEFRProgressBar
from german_tutor.widgets.streak_indicator import StreakIndicator


# Simple message class for navigation requests
class NavRequest(Message):
    def __init__(self, destination: str) -> None:
        super().__init__()
        self.destination = destination


class HomeScreen(Screen):
    """Main dashboard — shows lesson recommendation, progress, and navigation."""

    BINDINGS = [
        ("l", "nav_lessons", "Lessons"),
        ("q", "nav_quiz", "Quiz"),
        ("p", "nav_progress", "Progress"),
        ("r", "nav_review", "Review"),
        ("s", "nav_settings", "Settings"),
    ]

    def __init__(
        self,
        learner: Learner,
        recommendation: LessonRecommendation | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.learner = learner
        self.recommendation = recommendation

    def compose(self) -> ComposeResult:
        yield Header()

        # Sidebar navigation
        with Static(id="sidebar"):
            yield Static("Navigation", classes="nav-label")
            yield Button("📚 Lessons", id="nav-lessons", classes="nav-item")
            yield Button("🧠 Quiz", id="nav-quiz", classes="nav-item")
            yield Button("📊 Progress", id="nav-progress", classes="nav-item")
            yield Button("🔁 Review", id="nav-review", classes="nav-item")
            yield Button("⚙  Settings", id="nav-settings", classes="nav-item")

            yield Static("─" * 18, classes="text-muted")
            yield Static(
                f"Level: {self.learner.current_level.value}", classes="section-header"
            )
            yield StreakIndicator(self.learner.streak_days, id="streak")

        # Main content
        with Static(id="main-content"):
            yield Static(
                f"Welcome, {self.learner.name}!",
                classes="section-header",
            )
            yield CEFRProgressBar(
                current_level=self.learner.current_level.value,
                next_level=None,
                percent=0.0,
                id="cefr-bar",
            )

            if self.recommendation:
                yield Static("Recommended Next Lesson", classes="section-header")
                yield Static(
                    f"{self.recommendation.recommended_lesson_id} — {self.recommendation.lesson_title}",
                    id="rec-title",
                )
                yield Static(
                    self.recommendation.reason, id="rec-reason", classes="quiz-context"
                )
                if self.recommendation.english_speaker_warning:
                    yield Static(
                        f"⚠  {self.recommendation.english_speaker_warning}",
                        id="rec-warning",
                        classes="hint-text",
                    )
            else:
                yield Static(
                    "Loading recommendation...", id="rec-title", classes="loading"
                )
                yield Static("", id="rec-reason", classes="quiz-context")

            with Static(classes="action-buttons"):
                yield Button("Start Quiz", id="btn-quiz", variant="primary")
                yield Button("Next Lesson", id="btn-lesson", variant="success")

        yield Footer()

    def action_nav_lessons(self) -> None:
        self.app.post_message(NavRequest("lessons"))

    def action_nav_quiz(self) -> None:
        self.app.post_message(NavRequest("quiz"))

    def action_nav_progress(self) -> None:
        self.app.post_message(NavRequest("progress"))

    def action_nav_review(self) -> None:
        self.app.post_message(NavRequest("review"))

    def action_nav_settings(self) -> None:
        self.app.post_message(NavRequest("settings"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "nav-lessons":
            self.action_nav_lessons()
        elif button_id == "nav-quiz":
            self.action_nav_quiz()
        elif button_id == "nav-progress":
            self.action_nav_progress()
        elif button_id == "nav-settings":
            self.action_nav_settings()
        elif button_id == "btn-quiz":
            self.action_nav_quiz()
        elif button_id == "btn-lesson":
            self.action_nav_lessons()
        elif button_id == "nav-review":
            self.action_nav_review()

    def update_recommendation(self, rec: LessonRecommendation) -> None:
        """Update recommendation display after async load."""
        self.recommendation = rec
        try:
            self.query_one("#rec-title", Static).update(
                f"{rec.recommended_lesson_id} — {rec.lesson_title}"
            )
            self.query_one("#rec-reason", Static).update(rec.reason)
        except Exception:
            pass
