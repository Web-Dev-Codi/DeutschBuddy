from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable, Static


class GrammarPanelWidget(Widget):
    """Side-by-side EN↔DE grammar display panel.

    Renders lesson explanation with concept text, English comparison,
    and an optional table of forms.
    """

    def __init__(self, explanation: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.explanation = explanation

    def compose(self) -> ComposeResult:
        yield Static("## Grammar Explanation", classes="section-header")

        concept = self.explanation.get("concept", "").strip()
        if concept:
            yield Static(concept)

        english_comp = self.explanation.get("english_comparison", "").strip()
        if english_comp:
            yield Static("**English comparison:**", classes="section-header")
            yield Static(english_comp, classes="english-sentence")

        table_data = self.explanation.get("table")
        if table_data:
            yield Static(
                f"**{table_data.get('title', 'Reference Table')}**",
                classes="section-header",
            )
            table = DataTable()
            headers = table_data.get("headers", [])
            if headers:
                table.add_columns(*headers)
            for row in table_data.get("rows", []):
                table.add_row(*row)
            yield table
