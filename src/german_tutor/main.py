from __future__ import annotations

from datetime import datetime

from textual.app import App

from german_tutor.app_state import AppState
from german_tutor.curriculum.cefr import CEFRProgressionEngine
from german_tutor.curriculum.loader import CurriculumLoader
from german_tutor.db.connection import close_db, get_db
from german_tutor.db.migrations import run_migrations
from german_tutor.db.repositories.learner_repo import LearnerRepository
from german_tutor.db.repositories.progress_repo import ProgressRepository
from german_tutor.llm.client import OllamaClient
from german_tutor.llm.curriculum_agent import CurriculumAgent
from german_tutor.llm.quiz_agent import QuizAgent
from german_tutor.llm.tutor_agent import TutorAgent
from german_tutor.screens.help import HelpScreen
from german_tutor.screens.home import HomeScreen, NavRequest, VocabReviewScreen
from german_tutor.screens.lesson import LessonScreen
from german_tutor.screens.quiz import QuizScreen
from german_tutor.screens.results import ResultsScreen
from german_tutor.screens.settings import SettingsScreen


DEFAULT_LEARNER_NAME = "Learner"


class GermanTutorApp(App):
    """GermanTutor — AI-powered German language learning TUI."""

    TITLE = "GermanTutor"
    CSS_PATH = "styles/main.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("h", "go_home", "Home"),
        ("ctrl+r", "go_review", "Review"),
        ("?", "show_help", "Help"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._state: AppState | None = None
        self._current_lesson = None

    # ── Startup ──────────────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        """Initialise DB, agents, and load/create the learner."""
        db = await get_db()
        await run_migrations(db)

        client = OllamaClient()
        learner_repo = LearnerRepository(db)
        progress_repo = ProgressRepository(db)
        loader = CurriculumLoader()

        self._state = AppState(
            ollama_client=client,
            learner_repo=learner_repo,
            progress_repo=progress_repo,
            curriculum_loader=loader,
            curriculum_agent=CurriculumAgent(client),
            tutor_agent=TutorAgent(client),
            quiz_agent=QuizAgent(client),
            cefr_engine=CEFRProgressionEngine(),
            current_learner=None,
        )

        # Load or create learner (single-learner mode)
        learner = await learner_repo.get_first()
        if learner is None:
            learner = await learner_repo.create(DEFAULT_LEARNER_NAME)
        self._state.current_learner = learner

        await self._show_home()

    async def _show_home(self) -> None:
        """Push HomeScreen immediately; load recommendation in the background."""
        learner = self._state.current_learner
        screen = HomeScreen(learner=learner, recommendation=None)
        await self.push_screen(screen)
        self.run_worker(
            self._fetch_recommendation(screen),
            exclusive=False,
            name="recommendation",
        )

    async def _fetch_recommendation(self, screen: HomeScreen) -> None:
        """Background worker: compute lesson recommendation and update HomeScreen."""
        state = self._state
        learner = state.current_learner
        try:
            all_lessons = await state.curriculum_loader.load_all_async()
            progress = await state.progress_repo.get_all_progress(learner.id)
            completed_ids = {p.lesson_id for p in progress}
            current_level_lessons = all_lessons.get(learner.current_level.value, [])
            available = [l for l in current_level_lessons if l.id not in completed_ids]
            due_reviews = await state.progress_repo.get_due_reviews(
                learner.id, datetime.now()
            )
            perf_history = await state.progress_repo.get_recent_sessions(
                learner.id, limit=10
            )
            if not (available or due_reviews):
                return
            recommendation = await state.curriculum_agent.recommend_next_lesson(
                learner=learner,
                performance_history=perf_history,
                available_lessons=available,
                due_reviews=due_reviews,
            )
            if recommendation and screen.is_mounted:
                screen.update_recommendation(recommendation)
        except Exception:
            pass  # Ollama may not be running — degrade gracefully

    # ── Navigation ────────────────────────────────────────────────────────────

    def on_nav_request(self, message: NavRequest) -> None:
        """Handle navigation requests emitted by screens."""
        dest = message.destination
        if dest == "quiz":
            self.run_worker(self._start_quiz(), exclusive=True)
        elif dest == "lessons":
            self.run_worker(self._start_lesson(), exclusive=True)
        elif dest == "settings":
            self.run_worker(self._open_settings(), exclusive=True)
        elif dest == "review":
            self.run_worker(self._load_due_vocab_cards(), exclusive=True)
        elif dest in ("progress",):
            self.notify("Progress screen coming in a future update.")

    async def _start_lesson(self) -> None:
        """Push LessonScreen for the recommended or first available lesson."""
        if self._state is None:
            return
        state = self._state
        lesson = self._get_current_lesson()
        if lesson is None:
            self.notify("No lesson available.", severity="warning")
            return
        self._current_lesson = lesson
        screen = LessonScreen(
            lesson=lesson,
            learner=state.current_learner,
            tutor_agent=state.tutor_agent,
        )
        await self.push_screen(screen)

    async def _start_quiz(self) -> None:
        """Push QuizScreen and handle result."""
        if self._state is None:
            return
        state = self._state
        lesson = self._current_lesson or self._get_current_lesson()
        if lesson is None:
            self.notify("No lesson selected for quiz.", severity="warning")
            return

        screen = QuizScreen(
            lesson=lesson,
            learner=state.current_learner,
            quiz_agent=state.quiz_agent,
            progress_repo=state.progress_repo,
        )
        session = await self.push_screen_wait(screen)
        if session is not None:
            await self._show_results(session, lesson)

    async def _show_results(self, session, lesson) -> None:
        state = self._state
        screen = ResultsScreen(
            session=session,
            lesson=lesson,
            learner=state.current_learner,
            curriculum_agent=state.curriculum_agent,
            progress_repo=state.progress_repo,
        )
        result = await self.push_screen_wait(screen)
        if result == "next_lesson":
            await self._start_quiz()

    async def _open_settings(self) -> None:
        if self._state is None:
            return
        state = self._state
        screen = SettingsScreen(ollama_client=state.ollama_client)
        await self.push_screen(screen)

    async def _load_due_vocab_cards(self) -> None:
        """Worker: fetch due vocab cards then push VocabReviewScreen on the event loop."""
        if self._state is None:
            return
        state = self._state
        due = await state.progress_repo.get_due_vocab_cards(
            state.current_learner.id, datetime.now()
        )
        if not due:
            self.notify("No vocabulary cards due for review today!")
            return
        # Hand off to the event loop — push_screen_wait must not run inside a worker
        self.call_after_refresh(self._push_review_screen, due)

    async def _push_review_screen(self, due: list[dict]) -> None:
        """Push VocabReviewScreen and handle the result on the event loop."""
        if self._state is None:
            return
        screen = VocabReviewScreen(
            cards=due,
            progress_repo=self._state.progress_repo,
        )
        result = await self.push_screen_wait(screen)
        if result is not None:
            correct = result.get("correct", 0)
            total = result.get("total", 0)
            self.notify(f"Review complete: {correct}/{total} correct.")

    def _get_current_lesson(self):
        """Get the first available lesson for the current learner."""
        state = self._state
        if state is None:
            return None
        loader = state.curriculum_loader
        learner = state.current_learner
        try:
            lessons = loader.load_level(learner.current_level.value)
            if lessons:
                return lessons[0]
        except Exception:
            pass
        return None

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_go_review(self) -> None:
        self.run_worker(self._load_due_vocab_cards(), exclusive=True)

    def action_go_home(self) -> None:
        """Pop all screens above root, then push a fresh HomeScreen."""
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.run_worker(self._show_home(), exclusive=True)

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    # ── Teardown ──────────────────────────────────────────────────────────────

    async def on_unmount(self) -> None:
        await close_db()


def run() -> None:
    app = GermanTutorApp()
    app.run()


if __name__ == "__main__":
    run()
