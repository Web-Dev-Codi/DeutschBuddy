from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Label, Static


class HelpScreen(ModalScreen):
    """Modal overlay displaying all keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("?", "dismiss", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Static(id="help-container"):
            yield Static("Keyboard Shortcuts", id="help-title")
            table = DataTable(id="help-table", show_cursor=False)
            yield table
            yield Button("Close", id="help-close", variant="primary")

    def on_mount(self) -> None:
        table = self.query_one("#help-table", DataTable)
        table.add_columns("Key", "Action")
        table.add_rows(
            [
                ("q", "Quit"),
                ("h", "Home (dashboard)"),
                ("?", "Toggle this help"),
                ("Ctrl+R", "Review queue"),
                ("Escape", "Back / Close"),
                ("l", "Lessons (on Home)"),
                ("p", "Progress (on Home)"),
                ("r", "Review (on Home)"),
                ("s", "Settings (on Home)"),
            ]
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help-close":
            self.dismiss()

    def action_dismiss(self) -> None:
        self.dismiss()
