from __future__ import annotations

from textual.app import App

from deutschbuddy.app_state import AppState
from deutschbuddy.curriculum.cefr import CEFRProgressionEngine
from deutschbuddy.curriculum.loader import CurriculumLoader
from deutschbuddy.curriculum.vocab_loader import VocabLoader
from deutschbuddy.config import get_config
from deutschbuddy.db.connection import close_db, get_db
from deutschbuddy.db.migrations import run_migrations
from deutschbuddy.db.repositories.learner_repo import LearnerRepository
from deutschbuddy.db.repositories.progress_repo import ProgressRepository
from deutschbuddy.audio.listener import AudioListener
from deutschbuddy.audio.speaker import AudioSpeaker
from deutschbuddy.llm.client import OllamaClient
from deutschbuddy.llm.conversation_agent import ConversationAgent
from deutschbuddy.llm.curriculum_agent import CurriculumAgent
from deutschbuddy.llm.quiz_agent import QuizAgent
from deutschbuddy.llm.tutor_agent import TutorAgent
from deutschbuddy.screens.help import HelpScreen
from deutschbuddy.screens.home import HomeScreen, NavRequest
from deutschbuddy.screens.vocab_topics import VocabTopicsScreen
from deutschbuddy.screens.lesson import LessonScreen
from deutschbuddy.screens.quiz import QuizScreen
from deutschbuddy.screens.results import ResultsScreen
from deutschbuddy.screens.settings import SettingsScreen
from deutschbuddy.screens.conversation import ConversationScreen
from deutschbuddy.voice_conversation import VoiceConversationSession
from deutschbuddy.theme_manager import (
    register_neon_themes,
    load_saved_theme,
    apply_theme,
)


DEFAULT_LEARNER_NAME = "Learner"


class deutschbuddy(App):
    """deutschbuddy — AI-powered German language learning TUI."""

    TITLE = "deutschbuddy"
    CSS_PATH = "styles/main.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("h", "go_home", "Home"),
        # ("c", "go_conversation", "Conversation"),
        ("ctrl+r", "go_review", "Review"),
        ("?", "show_help", "Help"),
        ("t", "cycle_theme", "Theme"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._state: AppState | None = None
        self._current_lesson = None
        self._study_session_id: int | None = None

    @property
    def state(self) -> AppState:
        """Shared application state. Raises if accessed before on_mount completes."""
        if self._state is None:
            raise RuntimeError("AppState accessed before initialisation")
        return self._state

    # ── Startup ──────────────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        """Initialise DB, agents, and load/create the learner."""
        register_neon_themes(self)

        saved_theme = load_saved_theme()
        apply_theme(self, saved_theme)

        db = await get_db()
        await run_migrations(db)

        client = OllamaClient()
        learner_repo = LearnerRepository(db)
        progress_repo = ProgressRepository(db)
        loader = CurriculumLoader()
        vocab_loader = VocabLoader()

        self._state = AppState(
            ollama_client=client,
            learner_repo=learner_repo,
            progress_repo=progress_repo,
            curriculum_loader=loader,
            vocab_loader=vocab_loader,
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
        self._study_session_id = await progress_repo.start_app_study_session(learner.id)

        await self._show_home()

    async def _show_home(self) -> None:
        """Push HomeScreen with current lesson information."""
        learner = self._state.current_learner
        current_lesson = self._get_current_lesson()  # Remove await
        screen = HomeScreen(learner=learner, current_lesson=current_lesson)
        await self.push_screen(screen)

    # ── Navigation ────────────────────────────────────────────────────────────

    def on_nav_request(self, message: NavRequest) -> None:
        """Handle navigation requests emitted by screens."""
        dest = message.destination
        if dest == "quiz":
            self.run_worker(self._start_quiz(), exclusive=True)
        elif dest == "lessons":
            self.run_worker(self._start_lesson(), exclusive=True)
        elif dest == "lesson":
            lesson_id = message.kwargs.get("lesson_id")
            self.run_worker(self._start_lesson(lesson_id), exclusive=True)
        elif dest == "settings":
            self.run_worker(self._open_settings(), exclusive=True)
        elif dest == "review":
            self.run_worker(self._open_vocab_topics(), exclusive=True)
        elif dest in ("progress",):
            self.notify("Progress screen coming in a future update.")
        elif dest == "conversation":
            self.run_worker(self._start_conversation(), exclusive=True)

    async def _start_lesson(self, lesson_id: str | None = None) -> None:
        """Push LessonScreen for the recommended or specified lesson."""
        if self._state is None:
            return
        state = self._state

        if lesson_id:
            # Find the specific lesson by ID
            lesson = None
            for level in ["A1", "A2", "B1"]:
                try:
                    lessons = state.curriculum_loader.load_level(level)
                    lesson = next(
                        (
                            candidate
                            for candidate in lessons
                            if candidate.id == lesson_id
                        ),
                        None,
                    )
                    if lesson:
                        break
                except Exception as exc:
                    self.notify(f"Error loading level {level}: {exc}")
                    continue
            if lesson is None:
                self.notify(f"Lesson {lesson_id} not found.", severity="error")
                return
        else:
            # Use the current/recommended lesson
            lesson = self._get_current_lesson()
            if lesson is None:
                self.notify("No lesson available.", severity="warning")
                return

        self._current_lesson = lesson

        # Update learner's last lesson
        await state.learner_repo.update_last_lesson(state.current_learner.id, lesson.id)
        state.current_learner.last_lesson_id = lesson.id

        screen = LessonScreen(
            lesson=lesson,
            learner=state.current_learner,
            tutor_agent=state.tutor_agent,
            curriculum_loader=state.curriculum_loader,
        )
        await self.push_screen(screen)

    async def _start_quiz(self) -> None:
        """Push vocabulary preview then QuizScreen and handle result."""
        if self._state is None:
            return
        state = self._state
        lesson = self._current_lesson or self._get_current_lesson()
        if lesson is None:
            self.notify("No lesson selected for quiz.", severity="warning")
            return

        # Show vocabulary preview first
        from deutschbuddy.screens.vocab_preview import VocabPreviewScreen

        vocab_screen = VocabPreviewScreen(lesson=lesson, tutor_agent=state.tutor_agent)
        vocab_result = await self.push_screen_wait(vocab_screen)

        # Only proceed with quiz if user confirmed (didn't dismiss)
        if vocab_result is True:
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

    async def _open_vocab_topics(self) -> None:
        """Show the vocabulary topics grid for the learner's current level."""
        if self._state is None:
            return
        state = self._state
        screen = VocabTopicsScreen(
            learner=state.current_learner,
            vocab_loader=state.vocab_loader,
            progress_repo=state.progress_repo,
        )
        await self.push_screen(screen)

    def _get_current_lesson(self):
        """Get the learner's last lesson or first available lesson."""
        state = self._state
        if state is None:
            return None
        loader = state.curriculum_loader
        learner = state.current_learner

        # First try to get the learner's last lesson
        if learner.last_lesson_id:
            try:
                lesson = loader.get_lesson_by_id(learner.last_lesson_id)
                if lesson:
                    return lesson
            except Exception:
                pass

        # Fallback to first available lesson
        try:
            lessons = loader.load_level(learner.current_level.value)
            if lessons:
                return lessons[0]
        except Exception:
            pass
        return None

    async def _start_conversation(self) -> None:
        """Initialize and show conversation screen."""
        if self._state is None:
            return

        state = self._state
        conversation_config = get_config().get("conversation", {})

        listener = AudioListener(
            language=conversation_config.get("language", "de-DE"),
            model=conversation_config.get("whisper_model", "tiny"),
        )
        speaker = AudioSpeaker(
            voice=conversation_config.get("tts_voice", "de-DE"),
            rate=int(conversation_config.get("tts_rate", 150)),
        )
        agent = ConversationAgent(
            state.ollama_client,
        )
        session = VoiceConversationSession(
            listener=listener,
            speaker=speaker,
            agent=agent,
        )

        screen = ConversationScreen(
            session=session,
        )

        await self.push_screen(screen)

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_go_review(self) -> None:
        self.run_worker(self._open_vocab_topics(), exclusive=True)

    def action_go_conversation(self) -> None:
        self.run_worker(self._start_conversation(), exclusive=True)

    def action_go_home(self) -> None:
        """Pop all screens above root, then push a fresh HomeScreen."""
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.run_worker(self._show_home(), exclusive=True)

    def action_cycle_theme(self) -> None:
        """Cycle to the next available theme."""
        current = self.theme
        themes_list = list(self.available_themes.keys())
        try:
            current_idx = themes_list.index(current)
            next_idx = (current_idx + 1) % len(themes_list)
        except ValueError:
            next_idx = 0
        next_theme = themes_list[next_idx]
        apply_theme(self, next_theme)
        self.notify(f"Theme changed to {next_theme}", title="Theme")

    async def action_show_help(self) -> None:
        await self.push_screen(HelpScreen())

    # ── Teardown ──────────────────────────────────────────────────────────────

    async def on_unmount(self) -> None:
        if self._state is not None and self._study_session_id is not None:
            await self._state.progress_repo.end_app_study_session(self._study_session_id)
            self._study_session_id = None
        await close_db()


def run() -> None:
    app = deutschbuddy()
    app.run()


if __name__ == "__main__":
    run()
