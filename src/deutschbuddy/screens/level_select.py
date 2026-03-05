from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Label, RadioButton, RadioSet, Static

from deutschbuddy.models.lesson import CEFRLevel


class LevelSelectScreen(ModalScreen[CEFRLevel | None]):
    """Modal to select CEFR level (A1, A2, B1)."""

    BINDINGS = [
        Binding("escape", "dismiss_none", "Cancel", show=True),
        Binding("enter", "confirm", "Confirm", show=False),
        Binding("1", "select('A1')", show=False),
        Binding("2", "select('A2')", show=False),
        Binding("3", "select('B1')", show=False),
    ]

    def __init__(self, current: CEFRLevel | None = None) -> None:
        super().__init__()
        self.current = current or CEFRLevel.A1

    def compose(self) -> ComposeResult:
        with Static(id="level-select-container"):
            yield Label("Select Level", id="level-select-title")
            with RadioSet(id="level-radios"):
                yield RadioButton("A1", id="level-A1", value=(self.current == CEFRLevel.A1))
                yield RadioButton("A2", id="level-A2", value=(self.current == CEFRLevel.A2))
                yield RadioButton("B1", id="level-B1", value=(self.current == CEFRLevel.B1))
            with Static(id="level-select-actions"):
                yield Button("Confirm", id="level-confirm", variant="primary")
                yield Button("Cancel", id="level-cancel")

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def action_select(self, level: str) -> None:
        # Update radios by id when pressing 1/2/3
        radios = self.query_one("#level-radios", RadioSet)
        target_id = f"level-{level}"
        for rb in radios.query(RadioButton):
            rb.value = (rb.id == target_id)

    def action_confirm(self) -> None:
        radios = self.query_one("#level-radios", RadioSet)
        selected_level = None
        for rb in radios.query(RadioButton):
            if rb.value:
                # Extract level value from id: level-A1 / level-A2 / level-B1
                if rb.id and rb.id.startswith("level-"):
                    selected_level = rb.id.split("-", 1)[1]
                break
        if not selected_level:
            self.dismiss(None)
            return
        # Map back to CEFRLevel
        level = CEFRLevel(selected_level)
        self.dismiss(level)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "level-confirm":
            self.action_confirm()
        elif event.button.id == "level-cancel":
            self.dismiss(None)
