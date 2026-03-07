from __future__ import annotations

from pathlib import Path

from tomlkit import parse, dumps

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static, Select

from deutschbuddy.config import get_config
from deutschbuddy.theme_manager import THEME_CHOICES, apply_theme


_SETTINGS_PATH = Path(__file__).resolve().parents[3] / "config" / "settings.toml"


class SettingsScreen(Screen):
    """Model selection and Ollama host configuration."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, ollama_client=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.ollama_client = ollama_client
        self._available_models: list[str] = []
        self._config = get_config()
        self._current_theme = ""

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="main-content"):
            yield Static("Settings", classes="section-header")

            yield Static("Theme", classes="section-header")
            theme_options = [(name, key) for key, name in THEME_CHOICES.items()]
            yield Select(
                options=theme_options,
                value=self.app.theme
                if self.app.theme in THEME_CHOICES
                else "neon_cyberpunk",
                id="theme-select",
                prompt="Select a theme...",
            )

            app_config = self._config.get("app", {})
            conversation_config = self._config.get("conversation", {})

            yield Static("Ollama Host URL", classes="section-header")
            yield Input(
                value=self._config["ollama"].get("host", "http://localhost:11434"),
                id="host-input",
                placeholder="http://localhost:11434",
            )

            yield Static("Learner's Name", classes="section-header")
            yield Input(
                value=self._config["learner-name"]["name"],
                id="learner-name-input",
                placeholder="Enter your name",
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
                value=str(
                    app_config.get(
                        "daily_goal_minutes", self._config.get("daily_goal_minutes", 20)
                    )
                ),
                id="daily-goal-input",
                placeholder="20",
            )

            yield Static("Conversation Model", classes="section-header")
            yield Input(
                value=conversation_config.get(
                    "model",
                    self._config["ollama"].get(
                        "interaction_model", "mistral:7b-instruct"
                    ),
                ),
                id="conversation-model-input",
                placeholder="mistral:7b-instruct",
            )

            yield Static("Conversation Whisper Model", classes="section-header")
            yield Input(
                value=conversation_config.get("whisper_model", "tiny"),
                id="conversation-whisper-input",
                placeholder="tiny",
            )

            yield Static("Conversation Voice", classes="section-header")
            yield Input(
                value=conversation_config.get("tts_voice", "de-DE"),
                id="conversation-voice-input",
                placeholder="de-DE",
            )

            yield Static("Conversation Speech Rate", classes="section-header")
            yield Input(
                value=str(conversation_config.get("tts_rate", 150)),
                id="conversation-rate-input",
                placeholder="150",
            )

            yield Static("", id="available-models-label", classes="quiz-context")

            with Static(classes="action-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Refresh Models", id="btn-refresh", variant="default")
                yield Button("Back", id="btn-back", variant="default")

        yield Footer()

    async def on_mount(self) -> None:
        self._current_theme = (
            self.app.theme if self.app.theme in THEME_CHOICES else "neon_cyberpunk"
        )
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
        """Write updated values back to settings.toml and update learner goal/name."""
        host = self.query_one("#host-input", Input).value.strip()
        curriculum = self.query_one("#curriculum-model-input", Input).value.strip()
        interaction = self.query_one("#interaction-model-input", Input).value.strip()
        daily_goal_str = self.query_one("#daily-goal-input", Input).value.strip()
        conversation_model = self.query_one(
            "#conversation-model-input", Input
        ).value.strip()
        conversation_whisper = self.query_one(
            "#conversation-whisper-input", Input
        ).value.strip()
        conversation_voice = self.query_one(
            "#conversation-voice-input", Input
        ).value.strip()
        conversation_rate_str = self.query_one(
            "#conversation-rate-input", Input
        ).value.strip()
        learner_name = self.query_one("#learner-name-input", Input).value.strip()

        try:
            daily_goal = int(daily_goal_str) if daily_goal_str else 20
            daily_goal = max(1, min(180, daily_goal))
        except ValueError:
            daily_goal = 20

        try:
            conversation_rate = (
                int(conversation_rate_str) if conversation_rate_str else 150
            )
            conversation_rate = max(80, min(260, conversation_rate))
        except ValueError:
            conversation_rate = 150

        raw = _SETTINGS_PATH.read_text(encoding="utf-8")
        data = parse(raw)

        if "ollama" not in data:
            data.add("ollama", {})  # type: ignore[arg-type]
        if "app" not in data:
            data.add("app", {})  # type: ignore[arg-type]
        if "conversation" not in data:
            data.add("conversation", {})  # type: ignore[arg-type]
        if "learner-name" not in data:
            data.add("learner-name", {})  # type: ignore[arg-type]

        data["ollama"]["host"] = host  # type: ignore[index]
        data["ollama"]["curriculum_model"] = curriculum  # type: ignore[index]
        data["ollama"]["interaction_model"] = interaction  # type: ignore[index]
        data["app"]["daily_goal_minutes"] = daily_goal  # type: ignore[index]
        data["conversation"]["model"] = conversation_model or interaction  # type: ignore[index]
        data["conversation"]["whisper_model"] = conversation_whisper or "tiny"  # type: ignore[index]
        data["conversation"]["tts_voice"] = conversation_voice or "de-DE"  # type: ignore[index]
        data["conversation"]["tts_rate"] = conversation_rate  # type: ignore[index]
        data["learner-name"]["name"] = learner_name or "Learner"  # type: ignore[index]

        _SETTINGS_PATH.write_text(dumps(data), encoding="utf-8")

        if (
            hasattr(self.app, "_state")
            and self.app._state
            and self.app._state.current_learner
        ):
            learner = self.app._state.current_learner
            self.app.run_worker(
                self.app._state.learner_repo.update_goal(
                    learner.id,
                    daily_goal,
                )
            )
            learner.daily_goal_minutes = daily_goal
            if learner_name and learner_name != learner.name:
                self.app.run_worker(
                    self.app._state.learner_repo.update_name(
                        learner.id,
                        learner_name,
                    )
                )
                learner.name = learner_name

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.action_go_back()
        elif event.button.id == "btn-save":
            self._save_config()
            self._save_theme()
            self.notify("Settings saved. Restart to apply.", title="Saved")
        elif event.button.id == "btn-refresh":
            self.run_worker(self._refresh_models())

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle theme selection change."""
        if event.select.id == "theme-select":
            theme_name = event.value
            if theme_name and theme_name != Select.BLANK:
                self._current_theme = theme_name

    def _save_theme(self) -> None:
        """Save the selected theme."""
        if self._current_theme and self._current_theme != Select.BLANK:
            apply_theme(self.app, self._current_theme)
            self.notify(f"Theme changed to {self._current_theme}", title="Theme")
