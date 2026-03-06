from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from deutschbuddy.models.learner import Learner
 
from deutschbuddy.widgets.progress_bar import CEFRProgressBar
from deutschbuddy.widgets.streak_indicator import StreakIndicator
from deutschbuddy.screens.level_select import LevelSelectScreen


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
            yield Button("️ Voice Conversation", id="nav-conversation", classes="nav-item")
            yield Button("📚 Lessons", id="nav-lessons", classes="nav-item")
            yield Button("🧠 Quiz", id="nav-quiz", classes="nav-item")
            yield Button("📊 Progress", id="nav-progress", classes="nav-item")
            yield Button("🔁 Vocab Review", id="nav-review", classes="nav-item")
            yield Button("⚙  Settings", id="nav-settings", classes="nav-item")
            yield Button("🔄 Curriculum", id="nav-change-level", classes="nav-item")

            yield Static("─" * 18, classes="text-muted")
            yield Static(
                f"Level: {self.learner.current_level.value}", id="sidebar-level", classes="section-header"
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
        """Update daily goal display and progress bar when screen mounts."""
        self.run_worker(self._update_daily_goal(), exclusive=True)
        self.run_worker(self._update_progress_bar(), exclusive=True)

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

    async def _update_progress_bar(self) -> None:
        """Update the CEFR progress bar based on completed lessons."""
        try:
            if hasattr(self.app, '_state') and self.app._state:
                # Get all lessons for current level
                lessons = self.app._state.curriculum_loader.load_level(self.learner.current_level.value)
                lesson_ids = [lesson.id for lesson in lessons]
                
                # Get mastery scores for all lessons
                mastery_scores = await self.app._state.progress_repo.get_mastery_scores(
                    self.learner.id, lesson_ids
                )
                
                # Calculate progress percentage
                completed_lessons = sum(1 for score in mastery_scores.values() if score > 0)
                total_lessons = len(lessons)
                progress_percent = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0.0
                
                # Update progress bar
                progress_bar = self.query_one("#cefr-bar", CEFRProgressBar)
                progress_bar.update_progress(progress_percent)
        except Exception:
            # Fallback if anything goes wrong
            pass

    def action_nav_lessons(self) -> None:
        self.app.post_message(NavRequest("lessons"))

    def action_nav_quiz(self) -> None:
        self.app.post_message(NavRequest("quiz"))

    def action_nav_progress(self) -> None:
        self.app.post_message(NavRequest("progress"))

    def action_nav_review(self) -> None:
        self.app.post_message(NavRequest("review"))

    def action_nav_conversation(self) -> None:
        self.app.post_message(NavRequest("conversation"))

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
        elif button_id == "nav-conversation":
            self.action_nav_conversation()
        elif button_id == "nav-change-level":
            # Open modal to change level
            self.run_worker(self._change_level(), exclusive=True)

    async def _change_level(self) -> None:
        """Open level select modal, persist selection, refresh UI, and navigate."""
        try:
            current_level = self.learner.current_level
            selected = await self.app.push_screen_wait(LevelSelectScreen(current=current_level))
            if selected is None or selected == current_level:
                return

            # Persist to DB
            if hasattr(self.app, '_state') and self.app._state and self.learner.id is not None:
                try:
                    await self.app._state.learner_repo.update_level(self.learner.id, selected)
                    # Clear last lesson so the new level's first lesson is used
                    await self.app._state.learner_repo.update_last_lesson(self.learner.id, None)
                except Exception as exc:
                    self.notify(f"Failed to update level: {exc}", severity="error")
                    return

            # Update in-memory state
            self.learner.current_level = selected
            self.learner.last_lesson_id = None
            if hasattr(self.app, '_state') and self.app._state and self.app._state.current_learner is not None:
                self.app._state.current_learner.current_level = selected
                self.app._state.current_learner.last_lesson_id = None

            # Refresh sidebar label
            try:
                self.query_one("#sidebar-level", Static).update(f"Level: {selected.value}")
            except Exception:
                pass

            # Refresh CEFR progress bar label and progress
            try:
                bar = self.query_one("#cefr-bar", CEFRProgressBar)
                bar.update_levels(selected.value, None)
            except Exception:
                pass
            # Recompute percent based on new level
            await self._update_progress_bar()

            # Auto-navigate to recommended lesson for this level
            self.app.post_message(NavRequest("lessons"))
        except Exception:
            # Silently ignore unexpected errors to avoid crashing the UI
            pass
