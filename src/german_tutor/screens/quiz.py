from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from german_tutor.models.learner import Learner
from german_tutor.models.lesson import Lesson
from german_tutor.models.session import QuizResponse, QuizSession
from german_tutor.widgets.quiz_card import QuizCard


_MAX_FALLBACK_QUESTIONS = 5
_ANSWER_ADVANCE_DELAY_SECS = 1.5


class QuizScreen(Screen):
    """Full 10-question quiz flow with AI evaluation and progressive hints."""

    BINDINGS = [("escape", "quit_quiz", "Quit Quiz")]

    def __init__(
        self,
        lesson: Lesson,
        learner: Learner,
        quiz_agent=None,
        progress_repo=None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.lesson = lesson
        self.learner = learner
        self.quiz_agent = quiz_agent
        self.progress_repo = progress_repo
        self._questions: list[dict] = []
        self._current_index: int = 0
        self._responses: list[QuizResponse] = []
        self._session_id: int | None = None
        self._hint_level: int = 0
        self._advance_timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Static(id="main-content"):
            yield Static(f"Quiz — {self.lesson.title}", classes="section-header")
            yield Static("Loading questions...", id="quiz-status", classes="loading")
            yield Static(id="quiz-container")
            with Static(classes="action-buttons", id="quiz-actions"):
                yield Button("Submit", id="btn-submit", variant="primary")
                yield Button("Hint", id="btn-hint", variant="default")
                yield Button("Skip", id="btn-skip", variant="warning")
                yield Button("Break it down", id="btn-breakdown", variant="default")
        yield Footer()

    async def on_mount(self) -> None:
        # Use YAML quiz content directly instead of AI generation
        try:
            # Get quiz questions from YAML lesson data
            if hasattr(self.lesson, 'quiz') and self.lesson.quiz and 'questions' in self.lesson.quiz:
                self._questions = self.lesson.quiz['questions']
            else:
                # Fallback: create simple questions from example sentences if no quiz defined
                self._questions = self._create_fallback_questions()
            
            # Create a DB session record
            if self.progress_repo is not None and self.learner.id is not None:
                from german_tutor.models.session import QuizSession as QS
                from datetime import datetime

                new_session = QS(
                    learner_id=self.learner.id,
                    lesson_id=self.lesson.id,
                    started_at=datetime.now(),
                    total_questions=len(self._questions),
                )
                try:
                    self._session_id = await self.progress_repo.create_session(
                        new_session
                    )
                except Exception as e:
                    self.app.log.warning("Failed to create quiz session: %s", e)
            
            if self._questions:
                self.query_one("#quiz-status", Static).update(
                    f"Question 1 / {len(self._questions)}"
                )
                await self._show_question(0)
            else:
                self.query_one("#quiz-status", Static).update(
                    "No quiz questions available for this lesson."
                )
        except Exception as exc:
            self.query_one("#quiz-status", Static).update(
                f"Could not load quiz: {exc}"
            )

    def _create_fallback_questions(self) -> list[dict]:
        """Create simple questions from example sentences if no quiz defined in YAML."""
        questions = []
        for i, sentence in enumerate(self.lesson.example_sentences[:_MAX_FALLBACK_QUESTIONS]):
            german = sentence.get("german", "")
            english = sentence.get("english", "")
            if german and english:
                questions.append({
                    "type": "translation",
                    "question": f"Translate: {german}",
                    "correct_answer": english,
                    "context": f"From example sentence {i+1}",
                    "answer_explanation": f"This is the English translation of: {german}",
                    "grammar_rule_tested": "translation",
                    "hint": f"Think about the meaning of: {german.split()[0] if german.split() else german}",
                    "points": 10
                })
        return questions

    async def _show_question(self, index: int) -> None:
        """Render the question at the given index."""
        container = self.query_one("#quiz-container", Static)
        # Remove old quiz card if exists
        for card in container.query(QuizCard):
            await card.remove()
        q = self._questions[index]
        self._hint_level = 0
        card = QuizCard(question_data=q, question_number=index + 1)
        await container.mount(card)
        self.query_one("#quiz-status", Static).update(
            f"Question {index + 1} / {len(self._questions)}"
        )
        # Hide breakdown button on new question
        for b in self.query(Button):
            if b.id == "btn-breakdown":
                b.display = False
                break

    async def _submit_answer(self) -> None:
        """Evaluate the current answer and advance to next question."""
        card = next(iter(self.query(QuizCard)), None)
        if card is None:
            return

        answer = card.get_answer()
        if answer is None:
            return

        q = self._questions[self._current_index]
        q_type = q.get("type", "fill_blank")
        correct = q.get("correct_answer", "")
        is_correct = False
        evaluation: dict = {}

        if q_type == "multiple_choice":
            # Evaluate locally - both are strings
            is_correct = answer.strip().lower() == correct.strip().lower()
            evaluation = {
                "is_correct": is_correct,
                "score": 100 if is_correct else 0,
                "feedback": "Correct!" if is_correct else f"The answer is: {correct}",
            }
        elif q_type == "reorder":
            # Evaluate locally - both are lists
            try:
                # Convert answer string to list of ints if it's a string
                if isinstance(answer, str):
                    answer_list = [int(x.strip()) for x in answer.split()]
                else:
                    answer_list = answer
                
                is_correct = answer_list == correct
                evaluation = {
                    "is_correct": is_correct,
                    "score": 100 if is_correct else 0,
                    "feedback": "Correct!" if is_correct else f"The correct order is: {correct}",
                }
            except (ValueError, AttributeError):
                is_correct = False
                evaluation = {
                    "is_correct": False,
                    "score": 0,
                    "feedback": f"The correct order is: {correct}",
                }
        else:
            # LLM evaluation
            if self.quiz_agent is not None:
                try:
                    evaluation = await self.quiz_agent.evaluate_answer(
                        question=q.get("question", ""),
                        user_answer=answer,
                        correct_answer=correct,
                        grammar_rule=q.get("grammar_rule_tested", ""),
                        cefr_level=self.learner.current_level.value,
                    )
                    is_correct = evaluation.get("is_correct", False)
                except Exception as e:
                    self.app.log.warning("LLM evaluation failed, using fallback: %s", e)
                    is_correct = answer.strip().lower() == correct.strip().lower()
                    evaluation = {
                        "is_correct": is_correct,
                        "score": 100 if is_correct else 0,
                        "feedback": "Correct!" if is_correct else f"Answer: {correct}",
                    }

        card.show_feedback(is_correct, evaluation.get("feedback", ""))

        # Show breakdown button for wrong answers if there's context
        for b in self.query(Button):
            if b.id == "btn-breakdown":
                b.display = bool(not is_correct and q.get("context"))
                break

        response = QuizResponse(
            session_id=self._session_id,
            question_id=str(q.get("id", self._current_index)),
            user_answer=answer,
            is_correct=is_correct,
            llm_evaluation=evaluation,
        )
        self._responses.append(response)

        if self.progress_repo and self._session_id:
            try:
                await self.progress_repo.save_response(response)
            except Exception as e:
                self.app.log.warning("Failed to save quiz response: %s", e)

        # Advance after short delay
        self._advance_timer = self.set_timer(
            _ANSWER_ADVANCE_DELAY_SECS,
            lambda: self.run_worker(self._advance_question(), exclusive=True),
        )

    async def _advance_question(self) -> None:
        self._current_index += 1
        if self._current_index >= len(self._questions):
            await self._finish_quiz()
        else:
            await self._show_question(self._current_index)

    async def _finish_quiz(self) -> None:
        correct = sum(1 for r in self._responses if r.is_correct)
        total = len(self._responses)
        score = correct / total if total > 0 else 0.0

        if self.progress_repo and self._session_id:
            try:
                await self.progress_repo.complete_session(
                    self._session_id, correct, total, score, {}
                )
            except Exception as e:
                self.app.log.warning("Failed to complete quiz session: %s", e)

        session = QuizSession(
            id=self._session_id,
            learner_id=self.learner.id,
            lesson_id=self.lesson.id,
            total_questions=total,
            correct_answers=correct,
            score=score,
            responses=self._responses,
        )
        self.dismiss(session)

    async def _get_hint(self) -> None:
        card = next(iter(self.query(QuizCard)), None)
        if card is None:
            return

        self._hint_level = min(3, self._hint_level + 1)
        q = self._questions[self._current_index]

        if self.quiz_agent is not None:
            try:
                hint_data = await self.quiz_agent.get_hint(
                    question=q.get("question", ""),
                    correct_answer=q.get("correct_answer", ""),
                    grammar_rule=q.get("grammar_rule_tested", ""),
                    hint_level=self._hint_level,
                    attempted_answer=card.get_answer() or "",
                )
                card.show_hint(hint_data.get("hint_text", ""))
            except Exception as e:
                self.app.log.warning("LLM hint failed, using fallback: %s", e)
                card.show_hint(q.get("hint", ""))
        else:
            card.show_hint(q.get("hint", ""))

    def _show_breakdown(self) -> None:
        """Show breakdown screen for the current question's context."""
        if self._current_index < len(self._questions):
            q = self._questions[self._current_index]
            context = q.get("context", "")
            if context:
                from german_tutor.screens.breakdown import BreakdownScreen
                breakdown_screen = BreakdownScreen(
                    sentence=context,
                    cefr_level=self.learner.current_level.value,
                    tutor_agent=self.app.state.tutor_agent if hasattr(self.app, 'state') else None
                )
                self.app.push_screen(breakdown_screen)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-submit":
            self.run_worker(self._submit_answer(), exclusive=True)
        elif event.button.id == "btn-hint":
            self.run_worker(self._get_hint(), exclusive=True)
        elif event.button.id == "btn-skip":
            self.run_worker(self._advance_question(), exclusive=True)
        elif event.button.id == "btn-breakdown":
            self._show_breakdown()
        elif event.button.id == "btn-quit":
            self.action_quit_quiz()

    def action_quit_quiz(self) -> None:
        self.dismiss(None)

    def on_unmount(self) -> None:
        if self._advance_timer is not None:
            self._advance_timer.stop()
            self._advance_timer = None
