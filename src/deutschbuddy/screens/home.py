from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from deutschbuddy.models.learner import Learner
from deutschbuddy.screens.level_select import LevelSelectScreen
from deutschbuddy.widgets.progress_bar import CEFRProgressBar
from deutschbuddy.widgets.streak_indicator import StreakIndicator


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
        self._level_progress: tuple[int, int] = (0, 0)

    def compose(self) -> ComposeResult:
        yield Header()

        with Static(id="sidebar"):
            yield Static("Navigation", classes="nav-label")
            yield Button("📚 Lessons", id="nav-lessons", classes="nav-item")
            yield Button("🧠 Quiz", id="nav-quiz", classes="nav-item")
            yield Button("📊 Progress", id="nav-progress", classes="nav-item")
            yield Button("⚙  Settings", id="nav-settings", classes="nav-item")
            yield Button("🔄 Curriculum", id="nav-change-level", classes="nav-item")

            yield Static("─" * 18, classes="text-muted")
            yield Static(
                f"Level: {self.learner.current_level.value}", id="sidebar-level", classes="section-header"
            )
            yield StreakIndicator(self.learner.streak_days, id="streak")

        with Center(id="home-main-content"):
            with Static(id="home-shell"):
                yield Static(f"Welcome {self.learner.name}", id="home-welcome")
                yield Static(
                    f"Level: {self.learner.current_level.value}",
                    id="home-level-display",
                )
                yield CEFRProgressBar(
                    current_level=self.learner.current_level.value,
                    next_level=None,
                    percent=0.0,
                    show_label=False,
                    id="cefr-bar",
                )
                with Horizontal(id="home-widget-row"):
                    yield Static(id="stats-widget", classes="home-widget")
                    yield Button(
                        "Practice Vocabulary\n\nStart vocab practice\n\nOpen practice",
                        id="widget-vocab",
                        classes="home-widget home-widget-button",
                    )
                    yield Button(
                        "Continue Lesson\n\nChoose your next lesson\n\nOpen lessons",
                        id="widget-continue",
                        classes="home-widget home-widget-button",
                    )

        yield Footer()

    async def on_mount(self) -> None:
        self.run_worker(self._load_home_content(), exclusive=True)

    async def _load_home_content(self) -> None:
        if not hasattr(self.app, "_state") or not self.app._state:
            return

        state = self.app._state
        await self._update_progress_bar()

        minutes_today = await state.progress_repo.get_today_session_minutes(self.learner.id)
        vocab_count = await state.progress_repo.count_vocab_cards(self.learner.id)
        latest_vocab_progress = await state.progress_repo.get_latest_vocab_topic_progress(
            self.learner.id
        )

        self._update_stats_widget(minutes_today=minutes_today, vocab_count=vocab_count)
        self._update_vocab_widget(latest_vocab_progress)
        self._update_continue_widget()

    async def _update_progress_bar(self) -> None:
        if not hasattr(self.app, "_state") or not self.app._state:
            return

        lessons = self.app._state.curriculum_loader.load_level(
            self.learner.current_level.value
        )
        lesson_ids = [lesson.id for lesson in lessons]
        mastery_scores = await self.app._state.progress_repo.get_mastery_scores(
            self.learner.id,
            lesson_ids,
        )
        completed_lessons = sum(1 for score in mastery_scores.values() if score > 0)
        total_lessons = len(lessons)
        self._level_progress = (completed_lessons, total_lessons)
        progress_percent = (
            completed_lessons / total_lessons * 100 if total_lessons > 0 else 0.0
        )
        self.query_one("#cefr-bar", CEFRProgressBar).update_progress(progress_percent)

    def _update_stats_widget(self, *, minutes_today: float, vocab_count: int) -> None:
        completed_lessons, total_lessons = self._level_progress
        stats_text = (
            "Stats\n\n"
            f"Today\n{minutes_today:.0f} min\n\n"
            f"Lessons\n{completed_lessons}/{total_lessons}\n\n"
            f"Vocab\n{vocab_count} words"
        )
        self.query_one("#stats-widget", Static).update(stats_text)

    def _update_vocab_widget(self, latest_vocab_progress: dict[str, Any] | None) -> None:
        button = self.query_one("#widget-vocab", Button)
        if not hasattr(self.app, "_state") or not self.app._state or not latest_vocab_progress:
            button.label = "Practice Vocabulary\n\nStart vocab practice\n\nOpen practice"
            return

        topic_level = latest_vocab_progress.get("topic_level") or self.learner.current_level.value
        topic_id = latest_vocab_progress.get("topic_id")
        topic = self.app._state.vocab_loader.get_topic(topic_level, topic_id)
        if topic is None or not topic.words:
            button.label = "Practice Vocabulary\n\nStart vocab practice\n\nOpen practice"
            return

        current_index = int(latest_vocab_progress.get("current_word_index") or 0)
        next_index = min(current_index + 1, len(topic.words) - 1)
        next_word = topic.words[next_index]
        button.label = (
            "Practice Vocabulary\n\n"
            f"{next_word.german}\n"
            f"{topic.title}\n\n"
            "Open practice"
        )

    def _update_continue_widget(self) -> None:
        button = self.query_one("#widget-continue", Button)
        if self.current_lesson:
            button.label = (
                "Continue Lesson\n\n"
                f"{self.current_lesson.id}\n"
                f"{self.current_lesson.title}\n"
                f"{self.current_lesson.level.value} · {self.current_lesson.estimated_minutes} min"
            )
            return

        button.label = "Continue Lesson\n\nChoose your next lesson\n\nOpen lessons"

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
        elif button_id == "widget-vocab":
            self.action_nav_review()
        elif button_id == "widget-continue":
            if self.current_lesson:
                self.app.post_message(NavRequest("lesson", lesson_id=self.current_lesson.id))
            else:
                self.action_nav_lessons()
        elif button_id == "nav-change-level":
            self.run_worker(self._change_level(), exclusive=True)

    async def _change_level(self) -> None:
        try:
            current_level = self.learner.current_level
            selected = await self.app.push_screen_wait(LevelSelectScreen(current=current_level))
            if selected is None or selected == current_level:
                return

            if hasattr(self.app, '_state') and self.app._state and self.learner.id is not None:
                try:
                    await self.app._state.learner_repo.update_level(self.learner.id, selected)
                    await self.app._state.learner_repo.update_last_lesson(self.learner.id, None)
                except Exception as exc:
                    self.notify(f"Failed to update level: {exc}", severity="error")
                    return

            self.learner.current_level = selected
            self.learner.last_lesson_id = None
            self.current_lesson = None
            if hasattr(self.app, '_state') and self.app._state and self.app._state.current_learner is not None:
                self.app._state.current_learner.current_level = selected
                self.app._state.current_learner.last_lesson_id = None

            try:
                self.query_one("#sidebar-level", Static).update(f"Level: {selected.value}")
                self.query_one("#home-level-display", Static).update(f"Level: {selected.value}")
            except Exception:
                pass

            try:
                bar = self.query_one("#cefr-bar", CEFRProgressBar)
                bar.update_levels(selected.value, None)
            except Exception:
                pass
            await self._load_home_content()
        except Exception:
            pass
