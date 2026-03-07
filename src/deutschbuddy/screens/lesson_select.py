from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList, Static

from deutschbuddy.models.lesson import Lesson


class LessonSelectScreen(ModalScreen[str | None]):
    BINDINGS = [
        Binding("escape", "dismiss_none", "Close", show=True),
    ]

    def __init__(self, level: str, lessons: list[Lesson]) -> None:
        super().__init__()
        self.level = level
        self.lessons = lessons

    def compose(self) -> ComposeResult:
        with Static(id="lesson-select-container"):
            yield Label(f"{self.level} Curriculum", id="lesson-select-title")
            yield Static(
                f"{len(self.lessons)} lessons available",
                id="lesson-select-subtitle",
            )
            yield OptionList(
                *(lesson.title for lesson in self.lessons),
                id="lesson-option-list",
            )

    def on_mount(self) -> None:
        self.query_one("#lesson-option-list", OptionList).focus()

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        lesson = self.lessons[event.option_index]
        self.dismiss(lesson.id)
