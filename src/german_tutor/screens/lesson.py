from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static
from textual.containers import VerticalScroll, Horizontal

from german_tutor.models.learner import Learner
from german_tutor.models.lesson import Lesson
from german_tutor.widgets.grammar_panel import GrammarPanelWidget


class LessonScreen(Screen):
    """Displays a lesson with AI grammar explanation and sentence breakdowns."""

    BINDINGS = [("escape", "go_back", "Back"), ("q", "start_quiz", "Quiz")]

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
                yield Button("Start Quiz", id="btn-quiz", variant="primary")
                yield Button("Next Lesson", id="btn-next-lesson", variant="default")
                yield Button("Back", id="btn-back", variant="default")

        yield Footer()

    async def on_mount(self) -> None:
        """Use static YAML explanation without AI enhancement."""
        # The lesson explanation from YAML is already high-quality
        # No need for AI enhancement - this eliminates unnecessary AI calls
        pass

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_start_quiz(self) -> None:
        from german_tutor.screens.home import NavRequest

        self.app.post_message(NavRequest("quiz"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.action_go_back()
        elif event.button.id == "btn-quiz":
            self.action_start_quiz()
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
