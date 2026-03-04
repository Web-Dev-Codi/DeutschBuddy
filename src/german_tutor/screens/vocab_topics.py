from __future__ import annotations

from typing import Dict, List, Set

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static
from textual.containers import Center
from textual.reactive import reactive
from textual.message import Message

from german_tutor.db.repositories.progress_repo import ProgressRepository
from german_tutor.models.learner import Learner
from german_tutor.models.vocab import VocabTopic
from german_tutor.curriculum.vocab_loader import VocabLoader


class VocabTopicsScreen(Screen):
    """Grid of vocabulary topics for the current level."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(
        self,
        learner: Learner,
        vocab_loader: VocabLoader,
        progress_repo: ProgressRepository,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.learner = learner
        self.vocab_loader = vocab_loader
        self.progress_repo = progress_repo
        self._topics: List[VocabTopic] = []
        self._progress_map: Dict[str, dict] = {}
        self._summary: Dict[str, int] = {"total": 0, "completed": 0}

    def compose(self) -> ComposeResult:
        yield Header()
        with Static(id="main-content"):
            with Center():
                yield Static("Vocabulary Review", classes="section-header")
                yield Static("", id="topics-summary", classes="quiz-context")
                yield Button(
                    "Reset Progress",
                    id="btn-reset-vocab-topics",
                    variant="error",
                )
                with Center():
                    yield Static(id="topics-grid")
        yield Footer()

    async def on_mount(self) -> None:
        await self._load_and_render()

    async def _load_and_render(self) -> None:
        await self._load_data()
        await self._render_grid()

    async def _load_data(self) -> None:
        level = self.learner.current_level.value
        self._topics = self.vocab_loader.load_level(level)
        topic_ids = [t.id for t in self._topics]
        self._progress_map = await self.progress_repo.get_vocab_topic_progress_map(
            self.learner.id, topic_ids
        )
        self._summary = await self.progress_repo.get_vocab_topic_summary(
            self.learner.id
        )
        total_topics = self._summary.get("total") or len(self._topics)
        summary_text = (
            f"Completed {self._summary.get('completed', 0)}/"
            f"{total_topics} topics"
        )
        self.query_one("#topics-summary", Static).update(summary_text)

    async def _render_grid(self) -> None:
        grid = self.query_one("#topics-grid", Static)
        for child in list(grid.children):
            await child.remove()

        if not self._topics:
            await grid.mount(Static("No vocabulary topics found for this level."))
            return

        for topic in self._topics:
            progress = self._progress_map.get(topic.id, {})
            percent = float(progress.get("completed_percent") or 0)
            words_seen = int(progress.get("words_seen") or 0)
            status = "Done" if percent >= 100 else ("In progress" if words_seen > 0 else "Not started")
            label = (
                f"{topic.title}\n"
                f"{len(topic.words)} words\n"
                f"{percent:.0f}% · {status}"
            )
            variant = "success" if percent >= 100 else "primary" if words_seen > 0 else "default"
            btn = Button(
                label,
                id=f"topic-{topic.id}",
                classes=f"topic-card {variant}",
                variant=variant,
            )
            await grid.mount(btn)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "btn-reset-vocab-topics":
            self.run_worker(self._reset_all_topics(), exclusive=True)
            return
        if button_id.startswith("topic-"):
            topic_id = button_id.removeprefix("topic-")
            self.run_worker(self._open_topic(topic_id), exclusive=True)

    async def _reset_all_topics(self) -> None:
        await self.progress_repo.reset_vocab_topic_progress(self.learner.id)
        await self._load_and_render()

    async def _open_topic(self, topic_id: str) -> None:
        topic = next((t for t in self._topics if t.id == topic_id), None)
        if topic is None:
            return
        progress = self._progress_map.get(topic.id, {})
        screen = VocabFlashcardScreen(
            topic=topic,
            learner=self.learner,
            progress_repo=self.progress_repo,
            initial_progress=progress,
        )
        result = await self.app.push_screen_wait(screen)
        if result is not None:
            await self._load_and_render()

    def action_go_back(self) -> None:
        self.dismiss(None)


class VocabFlashcardScreen(Screen):
    """Flashcard navigator for a single vocabulary topic."""

    BINDINGS = [
        ("escape", "finish", "Done"),
        ("left", "prev", "Back"),
        ("right", "next", "Next"),
        ("space", "flip_card", "Flip Card"),
    ]

    class CardFlipped(Message):
        """Message sent when the card is flipped."""
        pass

    def __init__(
        self,
        topic: VocabTopic,
        learner: Learner,
        progress_repo: ProgressRepository,
        initial_progress: dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.topic = topic
        self.learner = learner
        self.progress_repo = progress_repo
        self._index = 0
        self._seen: Set[int] = set()
        self._initial_progress = initial_progress or {}
        self._showing_english = reactive(True)

    def compose(self) -> ComposeResult:
        yield Header()
        with Static(id="main-content"):
            yield Static(self.topic.title, classes="section-header")
            yield Static("", id="topic-progress", classes="quiz-context")
            with Center(id="flashcard-container", classes="flashcard-container"):
                with Static(id="flashcard", classes="flashcard"):
                    yield Static("", id="word-english", classes="flashcard-english")
                    yield Static("", id="word-german", classes="flashcard-german")
            with Center(classes="action-buttons"):
                yield Button("Back", id="btn-prev", variant="default")
                yield Button("Next", id="btn-next", variant="primary")
                yield Button("Done", id="btn-done", variant="success")
        yield Footer()

    async def on_mount(self) -> None:
        self._hydrate_seen_from_progress()
        await self._show_card(self._index)
        # Set up click handlers for flip functionality
        self.query_one("#flashcard").on_click = self._flip_card
        self.query_one("#word-english").on_click = self._flip_card
        self.query_one("#word-german").on_click = self._flip_card

    def _hydrate_seen_from_progress(self) -> None:
        total = len(self.topic.words)
        prior_seen = int(self._initial_progress.get("words_seen") or 0)
        capped = min(prior_seen, total)
        self._seen = set(range(capped))
        if capped > 0:
            self._index = min(capped, total - 1)

    async def _show_card(self, index: int) -> None:
        total = len(self.topic.words)
        index = max(0, min(index, total - 1))
        self._index = index
        word = self.topic.words[self._index]
        
        # Update both sides of the card
        self.query_one("#word-german", Static).update(word.german)
        self.query_one("#word-english", Static).update(word.english)
        
        # Reset to showing English side
        self._showing_english = True
        self._update_card_visibility()
        
        self._mark_seen(index)
        await self._persist_progress()
        self._update_progress_label()

    def _update_progress_label(self) -> None:
        total = len(self.topic.words)
        words_seen = len(self._seen)
        percent = min(100.0, (words_seen / total) * 100 if total else 0.0)
        self.query_one("#topic-progress", Static).update(
            f"Card {self._index + 1}/{total} • Seen {words_seen}/{total} ({percent:.0f}%)"
        )

    def _mark_seen(self, index: int) -> None:
        self._seen.add(index)

    async def _persist_progress(self) -> None:
        total = len(self.topic.words)
        words_seen = len(self._seen)
        percent = min(100.0, (words_seen / total) * 100 if total else 0.0)
        await self.progress_repo.upsert_vocab_topic_progress(
            learner_id=self.learner.id,
            topic_id=self.topic.id,
            topic_level=self.topic.level.value,
            total_words=total,
            words_seen=words_seen,
            completed_percent=percent,
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            self.run_worker(self._advance(1), exclusive=True)
        elif event.button.id == "btn-prev":
            self.run_worker(self._advance(-1), exclusive=True)
        elif event.button.id == "btn-done":
            self.action_finish()

    async def _advance(self, delta: int) -> None:
        new_index = self._index + delta
        total = len(self.topic.words)
        new_index = max(0, min(new_index, total - 1))
        await self._show_card(new_index)

    def action_next(self) -> None:
        self.run_worker(self._advance(1), exclusive=True)

    def action_prev(self) -> None:
        self.run_worker(self._advance(-1), exclusive=True)

    def action_finish(self) -> None:
        total = len(self.topic.words)
        words_seen = len(self._seen)
        percent = min(100.0, (words_seen / total) * 100 if total else 0.0)
        self.dismiss(
            {
                "topic_id": self.topic.id,
                "words_seen": words_seen,
                "completed_percent": percent,
            }
        )

    def action_flip_card(self) -> None:
        """Handle space bar to flip the card."""
        self._flip_card(None)

    def _flip_card(self, event) -> None:
        """Flip the card to show the other side."""
        self._showing_english = not self._showing_english
        self._update_card_visibility()
        self.post_message(self.CardFlipped())

    def _update_card_visibility(self) -> None:
        """Update visibility of card sides based on current state."""
        english_elem = self.query_one("#word-english")
        german_elem = self.query_one("#word-german")
        
        if self._showing_english:
            # English on top, German below
            english_elem.styles.layer = "above"
            german_elem.styles.layer = "below"
            english_elem.styles.visibility = "visible"
            german_elem.styles.visibility = "hidden"
        else:
            # German on top, English below
            english_elem.styles.layer = "below"
            german_elem.styles.layer = "above"
            english_elem.styles.visibility = "hidden"
            german_elem.styles.visibility = "visible"
