from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable, Static


class SentenceBreakdownWidget(Widget):
    """Word-by-word grammatical breakdown of a German sentence.

    Displays the German sentence, its English translation, and a table
    of each word's grammatical role, case, and English equivalent.
    """

    def __init__(self, breakdown_data: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = breakdown_data

    def compose(self) -> ComposeResult:
        german = self.data.get("german_sentence", "")
        english = self.data.get("english_translation", "")

        if german:
            yield Static(german, classes="german-sentence")
        if english:
            yield Static(f"→ {english}", classes="english-sentence")

        word_analysis = self.data.get("word_analysis", [])
        if word_analysis:
            table = DataTable()
            table.add_columns("Word", "English", "Part of Speech", "Case/Role", "Note")
            for word in word_analysis:
                note = word.get("english_comparison", "")
                if len(note) > 50:
                    note = note[:47] + "..."
                table.add_row(
                    word.get("german_word", ""),
                    word.get("english_equivalent", ""),
                    word.get("part_of_speech", ""),
                    word.get("grammatical_role", ""),
                    note,
                )
            yield table

        structure = self.data.get("structure_comparison")
        if structure:
            yield Static("**Word Order Comparison**", classes="section-header")
            yield Static(
                f"German: {structure.get('german_pattern', '')}",
                classes="german-sentence",
            )
            yield Static(
                f"English: {structure.get('english_pattern', '')}",
                classes="english-sentence",
            )
            diff = structure.get("key_difference", "")
            if diff:
                yield Static(diff)
