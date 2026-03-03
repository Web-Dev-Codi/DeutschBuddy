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
    def __init__(self, destination: str, **kwargs) -> None:
        super().__init__()
        self.destination = destination
        self.kwargs = kwargs


class HomeScreen(Screen):
    """Main dashboard — shows lesson recommendation, progress, and navigation."""

    BINDINGS = [
        ("l", "nav_lessons", "Lessons"),
        ("p", "nav_progress", "Progress"),
        ("r", "nav_review", "Review"),
        ("s", "nav_settings", "Settings"),
    ]

    def __init__(
        self,
        learner: Learner,
        current_lesson=None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.learner = learner
        self.current_lesson = current_lesson

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
            yield Static(id="daily-goal-bar", classes="daily-goal")

            if self.current_lesson:
                yield Static("Continue Where You Left Off", classes="section-header")
                yield Static(
                    f"{self.current_lesson.id} — {self.current_lesson.title}",
                    id="current-lesson-title",
                )
                yield Static(
                    f"Level: {self.current_lesson.level.value} | {self.current_lesson.estimated_minutes} min",
                    id="current-lesson-info",
                    classes="quiz-context"
                )
            else:
                yield Static("Start Learning", classes="section-header")
                yield Static(
                    "Choose your first lesson from the Lessons menu",
                    id="no-lesson-message",
                    classes="quiz-context"
                )

            with Static(classes="action-buttons"):
                yield Button("Start Quiz", id="btn-quiz", variant="primary")
                yield Button("Next Lesson", id="btn-lesson", variant="success")

        yield Footer()

    async def on_mount(self) -> None:
        """Update daily goal display when screen mounts."""
        self.run_worker(self._update_daily_goal(), exclusive=True)

    async def _update_daily_goal(self) -> None:
        """Update the daily goal progress display."""
        try:
            # Get progress repo from app state
            if hasattr(self.app, '_state') and self.app._state:
                minutes_today = await self.app._state.progress_repo.get_today_session_minutes(
                    self.learner.id
                )
                goal = self.learner.daily_goal_minutes
                
                if minutes_today >= goal:
                    display_text = f"Today: {minutes_today:.0f} / {goal} min ✓"
                else:
                    display_text = f"Today: {minutes_today:.0f} / {goal} min"
                
                self.query_one("#daily-goal-bar", Static).update(display_text)
        except Exception:
            # Fallback if anything goes wrong
            self.query_one("#daily-goal-bar", Static).update("Today: 0 / 20 min")

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
            if self.current_lesson:
                # Navigate to current lesson
                self.app.post_message(NavRequest("lesson", lesson_id=self.current_lesson.id))
            else:
                # No current lesson, go to lesson list
                self.action_nav_lessons()
        elif button_id == "nav-review":
            self.action_nav_review()
