from __future__ import annotations

import re
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from german_tutor.models.lesson import Lesson


class VocabPreviewScreen(Screen):
    """Vocabulary preview screen that shows key words before a quiz."""

    def __init__(self, lesson: Lesson, tutor_agent=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lesson = lesson
        self.tutor_agent = tutor_agent
        self._vocab_cards: list[dict] = []
        self._current_index: int = 0
        self._loading: bool = True

    def compose(self) -> ComposeResult:
        yield Header()
        with Static(id="main-content"):
            yield Static(f"Vocabulary Preview — {self.lesson.title}", classes="section-header")
            yield Static(
                "Review key vocabulary before starting the quiz",
                classes="quiz-context",
            )
            yield Static(id="word-display", classes="vocab-card")
            with Static(classes="action-buttons"):
                yield Button("Previous", id="btn-prev", variant="default")
                yield Button("Next", id="btn-next", variant="primary")
                yield Button("Start Quiz", id="btn-start", variant="success")
        yield Footer()

    async def on_mount(self) -> None:
        """Load vocabulary data in background."""
        self._update_display()
        
        # Start background worker to fetch vocabulary
        self.run_worker(self._load_vocabulary(), exclusive=True)

    async def _load_vocabulary(self) -> None:
        """Load vocabulary from lesson examples using tutor agent."""
        vocab_words = set()
        
        # Extract German words from example sentences
        for sent in self.lesson.example_sentences:
            german_text = sent.get('german', '')
            # Simple word extraction - split on whitespace and punctuation
            words = re.findall(r'\b\w+\b', german_text)
            vocab_words.update(words)
        
        # Create vocab cards
        self._vocab_cards = []
        
        if self.tutor_agent is not None:
            # Try to get enhanced vocabulary entries
            for word in sorted(vocab_words):
                if len(word) > 1:  # Skip single characters
                    try:
                        entry = await self.tutor_agent.get_vocabulary_entry(word, self.lesson.level.value)
                        self._vocab_cards.append({
                            'word': word,
                            'gender': entry.get('gender', ''),
                            'english': entry.get('english', ''),
                            'memory_trick': entry.get('memory_trick', '')
                        })
                    except Exception:
                        # Fallback to basic info
                        self._vocab_cards.append({
                            'word': word,
                            'gender': '',
                            'english': word,
                            'memory_trick': ''
                        })
        else:
            # Fallback when no tutor agent available
            for word in sorted(vocab_words):
                if len(word) > 1:
                    self._vocab_cards.append({
                        'word': word,
                        'gender': '',
                        'english': word,
                        'memory_trick': ''
                    })
        
        self._loading = False
        self._update_display()

    def _update_display(self) -> None:
        """Update the vocabulary display."""
        if self._loading:
            self.query_one("#word-display", Static).update("Loading vocabulary...")
            return
        
        if not self._vocab_cards:
            self.query_one("#word-display", Static).update("No vocabulary found.")
            return
        
        if self._current_index >= len(self._vocab_cards):
            self._current_index = 0
        elif self._current_index < 0:
            self._current_index = len(self._vocab_cards) - 1
        
        card = self._vocab_cards[self._current_index]
        
        display_text = f"[bold]{card['word']}[/bold]\n\n"
        if card['gender']:
            display_text += f"Gender: {card['gender']}\n"
        display_text += f"English: {card['english']}\n"
        if card['memory_trick']:
            display_text += f"\nMemory trick: {card['memory_trick']}"
        
        display_text += f"\n\n[dim]Card {self._current_index + 1} / {len(self._vocab_cards)}[/dim]"
        
        self.query_one("#word-display", Static).update(display_text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-prev":
            self._current_index -= 1
            self._update_display()
        elif event.button.id == "btn-next":
            self._current_index += 1
            self._update_display()
        elif event.button.id == "btn-start":
            self.dismiss(True)

    def action_go_back(self) -> None:
        """Go back without starting quiz."""
        self.dismiss(None)
