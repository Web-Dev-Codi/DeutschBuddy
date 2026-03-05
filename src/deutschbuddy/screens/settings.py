from __future__ import annotations

from pathlib import Path

from tomlkit import parse, dumps

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static

from deutschbuddy.config import get_config


_SETTINGS_PATH = Path(__file__).resolve().parents[3] / "config" / "settings.toml"


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

        raw = _SETTINGS_PATH.read_text(encoding="utf-8")
        data = parse(raw)

        # Ensure tables exist
        if "ollama" not in data:
            data.add("ollama", {})  # type: ignore[arg-type]
        if "app" not in data:
            data.add("app", {})  # type: ignore[arg-type]

        # Update values with roundtrip safety
        data["ollama"]["host"] = host  # type: ignore[index]
        data["ollama"]["curriculum_model"] = curriculum  # type: ignore[index]
        data["ollama"]["interaction_model"] = interaction  # type: ignore[index]
        data["daily_goal_minutes"] = daily_goal  # top-level present in current file

        _SETTINGS_PATH.write_text(dumps(data), encoding="utf-8")

        # Update learner's daily goal in database
        if hasattr(self.app, '_state') and self.app._state and self.app._state.current_learner:
            learner = self.app._state.current_learner
            self.app.run_worker(
                self.app._state.learner_repo.update_goal(
                    learner.id,
                    daily_goal,
                )
            )
            learner.daily_goal_minutes = daily_goal

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
