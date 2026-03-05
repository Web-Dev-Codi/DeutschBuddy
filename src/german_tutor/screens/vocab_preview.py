from __future__ import annotations

import asyncio
import re
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static, LoadingIndicator

from german_tutor.models.lesson import Lesson


class VocabPreviewScreen(Screen):
    """Vocabulary preview screen that shows key words before a quiz."""

    # Loading messages that will rotate
    LOADING_MESSAGES = [
        "AI is curating your personal vocabulary list...",
        "Analyzing lesson content for key terms...",
        "Generating custom memory aids for you...",
        "Preparing tailored vocabulary examples..."
    ]

    def __init__(self, lesson: Lesson, tutor_agent=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lesson = lesson
        self.tutor_agent = tutor_agent
        self._vocab_cards: list[dict] = []
        self._current_index: int = 0
        self._loading: bool = True
        self._loading_message_index: int = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Static(id="vocab-preview-container"):
            yield Static(f"Vocabulary Preview — {self.lesson.title}", classes="section-header")
            yield Static(
                "Review key vocabulary before starting the quiz",
                classes="quiz-context",
            )
            # Loading indicator and message
            with Static(id="loading-container", classes="loading-container"):
                yield LoadingIndicator(id="vocab-loading")
                yield Static("AI is curating your personal vocabulary list...", classes="loading-message")
                yield Static("Please wait", classes="loading-submessage")
            # Word display (hidden during loading)
            yield Static(id="word-display", classes="vocab-card")
            with Static(classes="action-buttons"):
                yield Button("Previous", id="btn-prev", variant="default")
                yield Button("Next", id="btn-next", variant="primary")
                yield Button("Start Quiz", id="btn-start", variant="success")
        yield Footer()

    async def on_mount(self) -> None:
        """Load vocabulary data in background."""
        self._update_display()
        
        # Start cycling loading messages
        self._cycle_loading_message()
        
        # Start background worker to fetch vocabulary
        self.run_worker(self._load_vocabulary(), exclusive=True)

    def _cycle_loading_message(self) -> None:
        """Cycle through loading messages every 2 seconds."""
        if self._loading:
            self._loading_message_index = (self._loading_message_index + 1) % len(self.LOADING_MESSAGES)
            self._update_display()
            # Schedule next message change
            self.set_timer(2.0, self._cycle_loading_message)

    async def _load_vocabulary(self) -> None:
        """Load vocabulary from lesson examples using tutor agent."""
        vocab_words = set()
        for sent in self.lesson.example_sentences:
            german_text = sent.get('german', '')
            words = re.findall(r'\b\w+\b', german_text)
            vocab_words.update(words)

        self._vocab_cards = []

        if self.tutor_agent is not None:
            sem = asyncio.Semaphore(5)

            async def fetch(word: str):
                if len(word) <= 1:
                    return None
                try:
                    async with sem:
                        entry = await asyncio.wait_for(
                            self.tutor_agent.get_vocabulary_entry(word, self.lesson.level.value),
                            timeout=10.0,
                        )
                    english_translation = (entry.get('english', '') or '').strip()
                    if not english_translation:
                        english_translation = "Translation unavailable"
                    memory_trick = (entry.get('memory_trick', '') or '').strip()
                    if not memory_trick:
                        if english_translation != "Translation unavailable":
                            memory_trick = f"Think of '{word}' as similar to '{english_translation}'"
                        else:
                            memory_trick = f"Practice saying '{word}' aloud to remember it"
                    if memory_trick.lower() == english_translation.lower() or memory_trick == f"Think of '{word}' as similar to 'Translation unavailable'":
                        memory_trick = f"Remember '{word}' by practicing it in context"
                    return {
                        'word': word,
                        'gender': entry.get('gender', ''),
                        'english': english_translation,
                        'memory_trick': memory_trick,
                    }
                except Exception:
                    return {
                        'word': word,
                        'gender': '',
                        'english': "Translation unavailable",
                        'memory_trick': f"Practice saying '{word}' aloud to remember it",
                    }

            tasks = [asyncio.create_task(fetch(w)) for w in sorted(vocab_words)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            self._vocab_cards = [r for r in results if isinstance(r, dict)]
        else:
            for word in sorted(vocab_words):
                if len(word) > 1:
                    self._vocab_cards.append({
                        'word': word,
                        'gender': '',
                        'english': "Translation unavailable",
                        'memory_trick': f"Try to associate '{word}' with a mental image",
                    })

        self._loading = False
        self._update_display()

    def _update_display(self) -> None:
        """Update the vocabulary display."""
        loading_container = self.query_one("#loading-container", Static)
        word_display = self.query_one("#word-display", Static)
        
        if self._loading:
            # Show loading indicator, hide word display
            loading_container.display = True
            word_display.display = False
            
            # Update loading message
            current_message = self.LOADING_MESSAGES[self._loading_message_index]
            loading_message = loading_container.query_one(".loading-message", Static)
            loading_message.update(current_message)
            return
        
        # Hide loading indicator, show word display
        loading_container.display = False
        word_display.display = True
        
        if not self._vocab_cards:
            word_display.update("No vocabulary found.")
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
        
        word_display.update(display_text)

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
