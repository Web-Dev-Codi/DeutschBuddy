from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static


class QuizCard(Widget):
    """Renders a single quiz question in the appropriate input style.

    Supports four question types:
    - multiple_choice: RadioSet with labelled options
    - fill_blank: Text Input with the blank shown in the prompt
    - translation: Text Input with the English sentence as prompt
    - reorder: Shows numbered shuffled words; learner types the sequence
    """

    DEFAULT_CSS = """
    QuizCard {
        border: round $primary;
        padding: 1 2;
        height: auto;
        margin-bottom: 1;
    }
    .quiz-question { text-style: bold; margin-bottom: 1; }
    .quiz-context { color: $text-muted; margin-bottom: 1; }
    .quiz-reorder-words { margin-bottom: 1; }
    .hint-text { color: $accent; margin-top: 1; }
    """

    def __init__(self, question_data: dict, question_number: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.question_data = question_data
        self.question_number = question_number
        self._hint_shown = False
        self._hint_level = 0

    def compose(self) -> ComposeResult:
        q = self.question_data
        q_type = q.get("type", "fill_blank")

        yield Static(
            f"Q{self.question_number}: {q.get('question', '')}",
            classes="quiz-question",
        )

        context = q.get("context")
        if context:
            yield Static(context, classes="quiz-context")

        if q_type == "multiple_choice":
            options = q.get("options") or []
            with RadioSet(id="answer-radio"):
                for opt in options:
                    yield RadioButton(opt)

        elif q_type in ("fill_blank", "translation"):
            yield Input(placeholder="Type your answer...", id="answer-input")

        elif q_type == "reorder":
            # Show shuffled words with numbers for the learner to reorder
            options = q.get("options") or []
            words_display = "  ".join(f"[{i + 1}] {w}" for i, w in enumerate(options))
            yield Static(words_display, classes="quiz-reorder-words")
            yield Input(
                placeholder="Type the correct order, e.g.: 3 1 4 2",
                id="answer-input",
            )

        yield Static("", id="hint-display", classes="hint-text")
        yield Button("Hint", id="hint-btn", variant="default")

    def get_answer(self) -> str | None:
        """Return the current user answer as a string, or None if empty."""
        q_type = self.question_data.get("type", "fill_blank")
        if q_type == "multiple_choice":
            try:
                radio_set = self.query_one(RadioSet)
                if radio_set.pressed_button is not None:
                    return radio_set.pressed_button.label.plain
            except Exception:
                pass
            return None
        else:
            try:
                return self.query_one(Input).value.strip() or None
            except Exception:
                return None

    def show_hint(self, hint_text: str) -> None:
        """Display hint text below the answer input."""
        self.query_one("#hint-display", Static).update(f"Hint: {hint_text}")

    def show_feedback(self, is_correct: bool, feedback: str) -> None:
        """Show post-submission feedback inline."""
        cls = "score-excellent" if is_correct else "score-needs-review"
        icon = "✓" if is_correct else "✗"
        hint = self.query_one("#hint-display", Static)
        hint.set_classes(f"hint-text {cls}")
        hint.update(f"{icon} {feedback}", markup=False)
