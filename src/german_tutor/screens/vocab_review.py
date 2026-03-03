# src/german_tutor/screens/vocab_review.py
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from german_tutor.curriculum.spaced_repetition import (
    CardState,
    calculate_next_review,
    score_to_quality,
)
from german_tutor.db.repositories.progress_repo import ProgressRepository
from german_tutor.widgets.quiz_card import QuizCard


class VocabReviewScreen(Screen):
    """Flashcard-style vocabulary review using SM-2 spaced repetition."""

    BINDINGS = [("escape", "quit_review", "Done")]

    def __init__(
        self,
        cards: list[dict],
        progress_repo: ProgressRepository,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._cards = cards
        self._progress_repo = progress_repo
        self._current_index: int = 0
        self._correct: int = 0
        self._answered: bool = False
        self._advance_timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Static(id="main-content"):
            yield Static("Vocabulary Review", classes="section-header")
            yield Static("", id="review-status", classes="loading")
            yield Static(id="review-container")
            with Static(classes="action-buttons", id="review-actions"):
                yield Button("Submit", id="btn-submit", variant="primary")
                yield Button("Skip", id="btn-skip", variant="warning")
                yield Button("Done", id="btn-done", variant="default")
        yield Footer()

    async def on_mount(self) -> None:
        if self._cards:
            await self._show_card(0)
        else:
            self.query_one("#review-status", Static).update("No cards to review.")

    async def _show_card(self, index: int) -> None:
        """Render the vocab card at the given index as a translation question."""
        card_data = self._cards[index]
        question_data = {
            "type": "translation",
            "question": card_data["german_word"],
            "correct_answer": card_data["english_word"],
            "context": f"Translate to English  •  Level: {card_data.get('level', '')}",
        }
        container = self.query_one("#review-container", Static)
        for widget in container.query(QuizCard):
            await widget.remove()
        quiz_card = QuizCard(question_data=question_data, question_number=index + 1)
        await container.mount(quiz_card)
        self._answered = False
        self.query_one("#review-status", Static).update(
            f"Card {index + 1} / {len(self._cards)}"
        )

    async def _submit_answer(self) -> None:
        """Evaluate answer, show feedback, update SM-2."""
        if self._answered:
            return
        try:
            quiz_card = self.query_one(QuizCard)
        except Exception:
            return

        answer = quiz_card.get_answer()
        if answer is None:
            return

        self._answered = True
        card_data = self._cards[self._current_index]
        correct_answer = card_data["english_word"]
        is_correct = answer.strip().lower() == correct_answer.strip().lower()

        if is_correct:
            self._correct += 1
            feedback = f"Correct! ({correct_answer})"
        else:
            feedback = f"The answer is: {correct_answer}"

        quiz_card.show_feedback(is_correct, feedback)

        # Update SM-2 for this card
        await self._update_sm2(card_data, is_correct)

        # Advance after a short delay
        self._advance_timer = self.set_timer(1.5, self._advance_card)

    async def _update_sm2(self, card_data: dict, is_correct: bool) -> None:
        """Apply SM-2 update and persist to DB."""
        quality = score_to_quality(100 if is_correct else 0)
        card = CardState(
            item_id=str(card_data["id"]),
            ease_factor=card_data.get("ease_factor") or 2.5,
            interval=card_data.get("interval_days") or 1,
            repetitions=card_data.get("repetitions") or 0,
        )
        updated = calculate_next_review(card, quality)
        try:
            await self._progress_repo.update_vocab_card_sm2(
                card_id=card_data["id"],
                ease=updated.ease_factor,
                interval=updated.interval,
                reps=updated.repetitions,
                next_review=updated.next_review,
            )
        except Exception as e:
            self.app.log.error(f"SM-2 update failed for card {card_data['id']}: {e}")
            self.app.notify("Could not save review progress", severity="warning")

    async def _advance_card(self) -> None:
        self._current_index += 1
        if self._current_index >= len(self._cards):
            await self._finish_review()
        else:
            await self._show_card(self._current_index)

    async def _finish_review(self) -> None:
        total = len(self._cards)
        self.dismiss({"correct": self._correct, "total": total})

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-submit":
            self.run_worker(self._submit_answer(), exclusive=True)
        elif event.button.id == "btn-skip":
            if self._advance_timer is not None:
                self._advance_timer.stop()
                self._advance_timer = None
            self.run_worker(self._advance_card(), exclusive=True)
        elif event.button.id == "btn-done":
            self.action_quit_review()

    def action_quit_review(self) -> None:
        self.dismiss(None)
