from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from german_tutor.config import get_config


class SettingsScreen(Screen):
    """Model selection and Ollama host configuration."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, ollama_client=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.ollama_client = ollama_client
        self._available_models: list[str] = []
        self._config = get_config()

    def compose(self) -> ComposeResult:
        yield Header()
        with Static(id="main-content"):
            yield Static("Settings", classes="section-header")

            yield Static("Ollama Host URL", classes="section-header")
            yield Input(
                value=self._config["ollama"].get("host", "http://localhost:11434"),
                id="host-input",
                placeholder="http://localhost:11434",
            )

            yield Static("Curriculum Model", classes="section-header")
            yield Input(
                value=self._config["ollama"].get(
                    "curriculum_model", "llama3.1:8b-instruct"
                ),
                id="curriculum-model-input",
                placeholder="llama3.1:8b-instruct",
            )

            yield Static("Interaction Model", classes="section-header")
            yield Input(
                value=self._config["ollama"].get(
                    "interaction_model", "mistral:7b-instruct"
                ),
                id="interaction-model-input",
                placeholder="mistral:7b-instruct",
            )

            yield Static("Daily Goal (minutes)", classes="section-header")
            yield Input(
                value=str(self._config.get("daily_goal_minutes", 20)),
                id="daily-goal-input",
                placeholder="20",
            )

            yield Static("", id="available-models-label", classes="quiz-context")

            with Static(classes="action-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Refresh Models", id="btn-refresh", variant="default")
                yield Button("Back", id="btn-back", variant="default")

        yield Footer()

    async def on_mount(self) -> None:
        if self.ollama_client is not None:
            await self._refresh_models()

    async def _refresh_models(self) -> None:
        try:
            self._available_models = await self.ollama_client.list_models()
            label = "Available models: " + ", ".join(self._available_models)
            self.query_one("#available-models-label", Static).update(label)
        except Exception as exc:
            self.query_one("#available-models-label", Static).update(
                f"Could not connect to Ollama: {exc}"
            )

    def _save_config(self) -> None:
        """Write updated values back to settings.toml and update learner goal."""
        host = self.query_one("#host-input", Input).value.strip()
        curriculum = self.query_one("#curriculum-model-input", Input).value.strip()
        interaction = self.query_one("#interaction-model-input", Input).value.strip()
        daily_goal_str = self.query_one("#daily-goal-input", Input).value.strip()

        # Validate daily goal
        try:
            daily_goal = int(daily_goal_str) if daily_goal_str else 20
            daily_goal = max(1, min(180, daily_goal))  # Reasonable bounds: 1 min to 3 hours
        except ValueError:
            daily_goal = 20

        config_path = Path("config/settings.toml")
        # Read raw content and do targeted replacements (tomllib is read-only)
        content = config_path.read_text()

        def replace_value(text: str, key: str, new_val: str) -> str:
            import re

            return re.sub(
                rf'^({key}\s*=\s*")[^"]*(")',
                rf"\g<1>{new_val}\g<2>",
                text,
                flags=re.MULTILINE,
            )

        content = replace_value(content, "host", host)
        content = replace_value(content, "curriculum_model", curriculum)
        content = replace_value(content, "interaction_model", interaction)
        
        # Handle daily_goal_minutes - it might not exist yet
        if "daily_goal_minutes" in content:
            content = replace_value(content, "daily_goal_minutes", str(daily_goal))
        else:
            # Add it to the end of the file
            content += f"\ndaily_goal_minutes = {daily_goal}\n"
        
        config_path.write_text(content)

        # Update learner's daily goal in database
        if hasattr(self.app, '_state') and self.app._state and self.app._state.current_learner:
            try:
                import asyncio
                asyncio.create_task(
                    self.app._state.learner_repo.update_goal(
                        self.app._state.current_learner.id, 
                        daily_goal
                    )
                )
                # Also update in-memory learner
                self.app._state.current_learner.daily_goal_minutes = daily_goal
            except Exception:
                pass  # Silently fail if DB update fails

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.action_go_back()
        elif event.button.id == "btn-save":
            self._save_config()
            self.notify("Settings saved. Restart to apply.", title="Saved")
        elif event.button.id == "btn-refresh":
            self.run_worker(self._refresh_models())
