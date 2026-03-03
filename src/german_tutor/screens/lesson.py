from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static
from textual.containers import VerticalScroll

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
                yield Static(
                    f"DE: {sent.get('german', '')}  |  EN: {sent.get('english', '')}",
                    classes="german-sentence",
                    id=f"sentence-{i}",
                )

            with Static(classes="action-buttons"):
                yield Button("Start Quiz", id="btn-quiz", variant="primary")
                yield Button("Next Lesson", id="btn-next-lesson", variant="default")
                yield Button("Back", id="btn-back", variant="default")

        yield Footer()

    async def on_mount(self) -> None:
        """Try to enhance explanation with AI after the screen mounts."""
        if self.tutor_agent is not None and not self._ai_enhancement_attempted:
            self._ai_enhancement_attempted = True
            try:
                ai_explanation = await self.tutor_agent.explain_lesson(
                    self.lesson, self.learner
                )
                # Replace the fallback explanation with AI-enhanced one
                self._explanation = ai_explanation
                # Update the grammar panel if it exists
                try:
                    grammar_panel = self.query_one("#grammar-panel", GrammarPanelWidget)
                    grammar_panel.update_content(ai_explanation)
                except Exception:
                    # Panel might not exist yet, that's fine
                    pass
            except Exception as exc:
                # Keep the fallback explanation, just log the error
                print(f"Could not enhance with AI explanation: {exc}")

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

    def action_next_lesson(self) -> None:
        """Navigate to the next lesson in the curriculum."""
        if self.curriculum_loader is None:
            self.notify("Cannot navigate to next lesson: curriculum not available")
            return
        
        try:
            # Get all lessons for the current level
            lessons = self.curriculum_loader.load_level(self.lesson.level.value)
            # Find current lesson index
            current_index = next((i for i, lesson in enumerate(lessons) if lesson.id == self.lesson.id), None)
            
            if current_index is not None and current_index < len(lessons) - 1:
                # Navigate to next lesson
                next_lesson = lessons[current_index + 1]
                from german_tutor.screens.home import NavRequest
                self.app.post_message(NavRequest("lesson", lesson_id=next_lesson.id))
            else:
                # No more lessons in this level
                self.notify("This is the last lesson in this level!")
        except Exception as exc:
            self.notify(f"Error navigating to next lesson: {exc}")
