from __future__ import annotations

import time
from datetime import datetime

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static
from textual.containers import VerticalScroll, Horizontal

from german_tutor.models.learner import Learner
from german_tutor.models.lesson import Lesson, LessonCategory
from german_tutor.widgets.grammar_panel import GrammarPanelWidget


class LessonScreen(Screen):
    """Displays a lesson with AI grammar explanation and sentence breakdowns."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(
        self,
        lesson: Lesson,
        learner: Learner,
        tutor_agent=None,
        curriculum_loader=None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.lesson = lesson
        self.learner = learner
        self.tutor_agent = tutor_agent
        self.curriculum_loader = curriculum_loader
        # Start with the lesson explanation as fallback
        self._explanation = lesson.explanation
        self._breakdowns: list[dict] = []
        self._ai_enhancement_attempted = False
        self._lesson_start_time = time.time()
        self._lesson_marked_complete = False
        self._complete_timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="main-content"):
            yield Static(
                f"{self.lesson.id} — {self.lesson.title}",
                classes="section-header",
            )
            yield Static(
                f"Level: {self.lesson.level.value}  |  "
                f"Category: {self.lesson.category.value}  |  "
                f"~{self.lesson.estimated_minutes} min",
                classes="quiz-context",
            )

            # Optional fundamentals panel rendered above the explanation for grammar lessons
            if self.lesson.category == LessonCategory.GRAMMAR and getattr(self.lesson, "fundamentals", None):
                fund = self.lesson.fundamentals or {}
                title = str(fund.get("title", "Grammar Fundamentals"))
                lines: list[str] = []
                # parts of speech
                pos = fund.get("parts_of_speech") or {}
                if isinstance(pos, dict):
                    definition = pos.get("definition")
                    if definition:
                        lines.append(str(definition).strip())
                    items = pos.get("items") or []
                    for it in items:
                        name = (it.get("name") if isinstance(it, dict) else None) or ""
                        note = (it.get("note") if isinstance(it, dict) else None) or ""
                        role = (it.get("role") if isinstance(it, dict) else None) or ""
                        extra = note or role
                        bullet = f"- {name}: {extra}" if extra else f"- {name}"
                        if name:
                            lines.append(bullet)
                # cases
                cases = fund.get("cases") or {}
                if isinstance(cases, dict):
                    definition = cases.get("definition")
                    if definition:
                        lines.append(str(definition).strip())
                    items = cases.get("items") or []
                    for it in items:
                        name = (it.get("name") if isinstance(it, dict) else None) or ""
                        role = (it.get("role") if isinstance(it, dict) else None) or ""
                        article = (it.get("article_clue") if isinstance(it, dict) else None) or ""
                        example = (it.get("example") if isinstance(it, dict) else None) or ""
                        details = "; ".join([s for s in [role, article, example] if s])
                        bullet = f"- {name}: {details}" if details else f"- {name}"
                        if name:
                            lines.append(bullet)
                # clauses
                clauses = fund.get("clauses") or {}
                if isinstance(clauses, dict):
                    definition = clauses.get("definition")
                    if definition:
                        lines.append(str(definition).strip())
                    notes = clauses.get("notes") or []
                    for note in notes:
                        lines.append(f"- {str(note)}")
                yield Static(title, classes="section-header")
                yield Static("\n".join(lines), classes="quiz-context", id="fundamentals-panel")

            if self._explanation:
                yield GrammarPanelWidget(self._explanation, id="grammar-panel")
            else:
                yield Static(
                    "Loading AI explanation...", id="grammar-loading", classes="loading"
                )

            yield Static("Example Sentences", classes="section-header")
            for i, sent in enumerate(self.lesson.example_sentences[:3]):
                with Horizontal(classes="sentence-container"):
                    yield Static(
                        f"DE: {sent.get('german', '')}  |  EN: {sent.get('english', '')}",
                        classes="german-sentence",
                        id=f"sentence-{i}",
                    )
                    yield Button("Analyse", id=f"btn-analyse-{i}", variant="default")

            with Static(classes="action-buttons"):
                yield Button("Back", id="btn-back", variant="error")
                yield Button("Next Lesson", id="btn-next-lesson", variant="success")

        yield Footer()

    async def on_mount(self) -> None:
        """Use static YAML explanation without AI enhancement."""
        # The lesson explanation from YAML is already high-quality
        # No need for AI enhancement - this eliminates unnecessary AI calls
        
        # Start a timer to check for lesson completion after 1 minute
        self._complete_timer = self.set_timer(60.0, self._check_lesson_completion)

    def action_go_back(self) -> None:
        """Navigate to the previous lesson in the curriculum, or home if none."""
        if self.curriculum_loader is None:
            # Fallback: if we have no curriculum, behave like a simple back
            if hasattr(self.app, "_stack") and len(self.app._stack) > 1:
                self.app.pop_screen()
            else:
                self.app.action_go_home()
            return

        try:
            current_lesson = self.curriculum_loader.get_lesson_by_id(self.lesson.id)
            if current_lesson is None:
                self.notify(
                    f"Could not find current lesson {self.lesson.id} in the curriculum!"
                )
                return

            lessons = self.curriculum_loader.load_level(current_lesson.level.value)

            current_index = None
            for i, lesson in enumerate(lessons):
                if lesson.id == current_lesson.id:
                    current_index = i
                    break

            if current_index is None:
                self.notify(
                    f"Could not find current lesson {current_lesson.id} in the curriculum!"
                )
                return

            if current_index > 0:
                previous_lesson = lessons[current_index - 1]
                from german_tutor.screens.home import NavRequest

                self.app.post_message(
                    NavRequest("lesson", lesson_id=previous_lesson.id)
                )
            else:
                # This is the very first lesson in the level; go home
                self.app.action_go_home()
        except Exception as exc:
            self.notify(f"Error navigating to previous lesson: {exc}")

    def _check_lesson_completion(self) -> None:
        """Check if lesson has been active for more than 1 minute and mark as complete."""
        if not self._lesson_marked_complete and hasattr(self.app, '_state') and self.app._state:
            # Mark lesson as complete
            self._lesson_marked_complete = True
            
            # Create lesson progress record
            from german_tutor.models.lesson import LessonProgress
            progress = LessonProgress(
                learner_id=self.learner.id,
                lesson_id=self.lesson.id,
                completed_at=datetime.now(),
                attempts=1,
                last_score=1.0,  # Auto-complete gives full score
                mastery_score=1.0,
                next_review=None
            )
            
            # Save progress in background
            self.run_worker(self._save_lesson_progress(progress), exclusive=False)
            
            # Notify user with success coloring
            self.notify(f"Lesson {self.lesson.id} marked as complete!", severity="success")

    async def _save_lesson_progress(self, progress) -> None:
        """Save lesson progress to database."""
        try:
            await self.app._state.progress_repo.upsert_lesson_progress(progress)
        except Exception as e:
            self.notify(f"Error saving progress: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.action_go_back()
        elif event.button.id == "btn-next-lesson":
            self.action_next_lesson()
        elif event.button.id and event.button.id.startswith("btn-analyse-"):
            # Extract the sentence index from the button ID
            try:
                index = int(event.button.id.split("-")[-1])
                if index < len(self.lesson.example_sentences):
                    german_sentence = self.lesson.example_sentences[index].get('german', '')
                    if german_sentence:
                        from german_tutor.screens.breakdown import BreakdownScreen
                        breakdown_screen = BreakdownScreen(
                            sentence=german_sentence,
                            cefr_level=self.learner.current_level.value,
                            tutor_agent=self.tutor_agent
                        )
                        self.app.push_screen(breakdown_screen)
            except (ValueError, IndexError):
                pass  # Invalid button ID, ignore

    def action_next_lesson(self) -> None:
        """Navigate to the next lesson in the curriculum."""
        if self.curriculum_loader is None:
            self.notify("Cannot navigate to next lesson: curriculum not available")
            return
        
        try:
            # Get the current lesson from the curriculum to ensure we have the right object
            current_lesson = self.curriculum_loader.get_lesson_by_id(self.lesson.id)
            if current_lesson is None:
                self.notify(f"Could not find current lesson {self.lesson.id} in the curriculum!")
                return
            
            # Get all lessons for the current level
            lessons = self.curriculum_loader.load_level(current_lesson.level.value)
            
            # Find current lesson index
            current_index = None
            for i, lesson in enumerate(lessons):
                if lesson.id == current_lesson.id:
                    current_index = i
                    break
            
            if current_index is None:
                self.notify(f"Could not find current lesson {current_lesson.id} in the curriculum!")
                return
            
            if current_index < len(lessons) - 1:
                # Navigate to next lesson
                next_lesson = lessons[current_index + 1]
                from german_tutor.screens.home import NavRequest
                self.notify(f"Attempting to navigate to: {next_lesson.id}")
                self.app.post_message(NavRequest("lesson", lesson_id=next_lesson.id))
            else:
                # No more lessons in this level
                self.notify("This is the last lesson in this level!")
        except Exception as exc:
            self.notify(f"Error navigating to next lesson: {exc}")
            import traceback
            self.notify(f"Full error: {traceback.format_exc()}")

    def on_unmount(self) -> None:
        if self._complete_timer is not None:
            self._complete_timer.stop()
            self._complete_timer = None
