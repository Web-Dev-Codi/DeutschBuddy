from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from german_tutor.models.learner import Learner
from german_tutor.models.lesson import Lesson
from german_tutor.models.session import QuizSession


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
                if pct >= 85
                else "score-good"
                if pct >= 60
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
        """Generate AI coaching report and update SM-2 after mounting."""
        if self.curriculum_agent is not None and self.progress_repo is not None:
            try:
                # Build question breakdown for analysis
                breakdown = []
                for r in self.session.responses:
                    breakdown.append(
                        {
                            "question_id": r.question_id,
                            "is_correct": r.is_correct,
                            "user_answer": r.user_answer,
                            "evaluation": r.llm_evaluation or {},
                        }
                    )
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
                    self.learner.id, limit=5
                )
                self._analysis = (
                    await self.curriculum_agent.generate_performance_analysis(
                        learner=self.learner,
                        session_results=session_results,
                        question_breakdown=breakdown,
                        history=history,
                    )
                )
                coach_msg = self._analysis.get("coach_message", "")
                self.query_one("#analysis-display", Static).update(coach_msg)

                # Update lesson progress with SM-2
                await self._update_progress()
            except Exception as exc:
                self.query_one("#analysis-display", Static).update(
                    f"Analysis unavailable: {exc}"
                )

    async def _update_progress(self) -> None:
        """Update mastery score and spaced repetition schedule."""
        from datetime import datetime
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
                ease_factor=2.5,
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
        )
        await self.progress_repo.upsert_lesson_progress(progress)

    def action_go_home(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-home":
            self.action_go_home()
        elif event.button.id == "btn-next":
            self.dismiss("next_lesson")
