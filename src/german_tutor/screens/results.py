from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from german_tutor.models.learner import Learner
from german_tutor.models.lesson import Lesson
from german_tutor.models.session import QuizSession


_GRADE_EXCELLENT_THRESHOLD = 85
_GRADE_GOOD_THRESHOLD = 60
_HISTORY_LIMIT = 5


class ResultsScreen(Screen):
    """Post-quiz analysis — shows score, AI coaching, and next lesson recommendations."""

    BINDINGS = [("escape", "go_home", "Home")]

    def __init__(
        self,
        session: QuizSession,
        lesson: Lesson,
        learner: Learner,
        curriculum_agent=None,
        progress_repo=None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.session = session
        self.lesson = lesson
        self.learner = learner
        self.curriculum_agent = curriculum_agent
        self.progress_repo = progress_repo
        self._analysis: dict | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Static(id="main-content"):
            correct = self.session.correct_answers
            total = self.session.total_questions or 1
            pct = round((correct / total) * 100)
            grade_class = (
                "score-excellent"
                if pct >= _GRADE_EXCELLENT_THRESHOLD
                else "score-good"
                if pct >= _GRADE_GOOD_THRESHOLD
                else "score-needs-review"
            )
            yield Static(
                f"Session Results — {self.lesson.title}",
                classes="section-header",
            )
            yield Static(
                f"Score: {correct}/{total}  ({pct}%)",
                id="score-display",
                classes=grade_class,
            )

            yield Static("AI Analysis", classes="section-header")
            yield Static(
                "Loading coaching report...", id="analysis-display", classes="loading"
            )

            with Static(classes="action-buttons"):
                yield Button("Next Lesson", id="btn-next", variant="primary")
                yield Button("Home", id="btn-home", variant="default")

        yield Footer()

    async def on_mount(self) -> None:
        """Run persistence side effects before attempting AI analysis."""
        if self.progress_repo is not None:
            await self._update_progress()
            await self._check_daily_goal()
            await self._upsert_vocab_cards()

        if (
            self.curriculum_agent is not None
            and self.progress_repo is not None
        ):
            await self._run_ai_analysis()

    async def _run_ai_analysis(self) -> None:
        """Fetch coaching report; failures only affect display."""
        try:
            breakdown = [
                {
                    "question_id": r.question_id,
                    "is_correct": r.is_correct,
                    "user_answer": r.user_answer,
                    "evaluation": r.llm_evaluation or {},
                }
                for r in self.session.responses
            ]
            session_results = {
                "lesson_title": self.lesson.title,
                "correct": self.session.correct_answers,
                "total": self.session.total_questions,
                "score_percent": round(
                    (
                        self.session.correct_answers
                        / (self.session.total_questions or 1)
                    )
                    * 100,
                    1,
                ),
            }
            history = await self.progress_repo.get_recent_sessions(
                self.learner.id, limit=_HISTORY_LIMIT
            )
            self._analysis = await self.curriculum_agent.generate_performance_analysis(
                learner=self.learner,
                session_results=session_results,
                question_breakdown=breakdown,
                history=history,
            )
            coach_msg = self._analysis.get("coach_message", "")
            self.query_one("#analysis-display", Static).update(coach_msg)
        except Exception as exc:
            self.query_one("#analysis-display", Static).update(
                f"Analysis unavailable: {exc}"
            )

    async def _update_progress(self) -> None:
        """Update mastery score and spaced repetition schedule."""
        from german_tutor.curriculum.spaced_repetition import (
            CardState,
            calculate_next_review,
            score_to_quality,
        )
        from german_tutor.models.lesson import LessonProgress

        score_pct = round(
            (self.session.correct_answers / (self.session.total_questions or 1)) * 100
        )
        quality = score_to_quality(score_pct)

        existing = await self.progress_repo.get_lesson_progress(
            self.learner.id, self.lesson.id
        )
        if existing:
            card = CardState(
                item_id=self.lesson.id,
                ease_factor=existing.ease_factor,
                interval=1,
                repetitions=existing.attempts,
            )
        else:
            card = CardState(item_id=self.lesson.id)

        updated_card = calculate_next_review(card, quality)

        progress = LessonProgress(
            learner_id=self.learner.id,
            lesson_id=self.lesson.id,
            completed_at=datetime.now(),
            attempts=(existing.attempts + 1) if existing else 1,
            last_score=self.session.score,
            mastery_score=min(1.0, self.session.score),
            next_review=updated_card.next_review,
            ease_factor=updated_card.ease_factor,
        )
        await self.progress_repo.upsert_lesson_progress(progress)
        await self._update_streak()

    async def _update_streak(self) -> None:
        """Update learner streak after session save."""
        from german_tutor.curriculum.streak import calculate_streak

        try:
            learner_repo = self.app.state.learner_repo
        except RuntimeError:
            return
        if self.learner is None or self.learner.id is None:
            return

        new_streak = calculate_streak(
            self.learner.last_session_date, self.learner.streak_days
        )
        now = datetime.now()
        try:
            await learner_repo.update_streak(self.learner.id, new_streak, now)
        except Exception as e:
            self.app.log.error(f"Failed to update streak: {e}")
            return  # don't update in-memory if DB failed

        # Update both self.learner and state.current_learner so they stay consistent
        self.learner.streak_days = new_streak
        self.learner.last_session_date = now
        if hasattr(self.app, '_state') and self.app._state and self.app._state.current_learner is not None:
            self.app._state.current_learner.streak_days = new_streak
            self.app._state.current_learner.last_session_date = now

    async def _upsert_vocab_cards(self) -> None:
        """Extract vocabulary from lesson example sentences and upsert to DB."""
        level = self.lesson.level.value
        entries = [
            (german, english, level)
            for entry in self.lesson.example_sentences
            if (german := entry.get("german", "").strip())
            and (english := entry.get("english", "").strip())
        ]
        try:
            await self.progress_repo.upsert_vocab_cards_bulk(
                self.learner.id, entries
            )
        except Exception as e:
            self.app.log.error(f"Failed to upsert vocab cards: {e}")

    async def _check_daily_goal(self) -> None:
        """Check if daily goal was reached and show notification."""
        try:
            minutes_today = await self.progress_repo.get_today_session_minutes(
                self.learner.id
            )
            if minutes_today >= self.learner.daily_goal_minutes:
                self.notify(
                    "Daily goal reached! Great work.",
                    title="Goal Complete"
                )
        except Exception as e:
            self.app.log.error(f"Failed to check daily goal: {e}")

    def action_go_home(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-home":
            self.action_go_home()
        elif event.button.id == "btn-next":
            self.dismiss("next_lesson")
