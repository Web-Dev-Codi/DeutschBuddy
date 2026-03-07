"""Conversation screen with push-to-talk interface."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Button, Footer, Header, Static

from deutschbuddy.voice_conversation import ConversationTurn, VoiceConversationSession


class ConversationScreen(Screen):
    """Main conversation interface with push-to-talk."""

    BINDINGS = [
        Binding("space", "capture_turn", "Speak", show=False),
        Binding("s", "start_conversation", "Start"),
        Binding("x", "stop_conversation", "Stop"),
        Binding("escape", "close", "Close"),
    ]

    def __init__(
        self,
        session: VoiceConversationSession,
    ):
        super().__init__()
        self.session = session
        self.is_busy = False
        self.conversation_history: list[ConversationTurn] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="status-bar", classes="status-bar")

        with VerticalScroll(id="conversation-area"):
            yield Static(id="conversation-transcript", classes="conversation-transcript")

        with Static(classes="action-buttons"):
            yield Button("Start Conversation", id="start-btn", variant="success")
            yield Button("Speak", id="speak-btn", variant="primary")
            yield Button("Stop", id="stop-btn", variant="error")

        yield Static(
            "Starten Sie das Gespräch und drücken Sie dann LEERTASTE oder Speak.",
            id="instructions",
            classes="quiz-context",
        )

        yield Footer()

    def on_mount(self) -> None:
        self._update_status("Gestoppt")
        self._render_transcript()
        self._update_controls()

    def on_unmount(self) -> None:
        self.session.stop()

    def action_start_conversation(self) -> None:
        if self.is_busy or self.session.is_active:
            return
        self.run_worker(self._start_session(), exclusive=True)

    def action_capture_turn(self) -> None:
        if self.is_busy:
            return
        if not self.session.is_active:
            self.notify("Starten Sie zuerst das Gespräch.", severity="warning")
            return
        self.run_worker(self._process_turn(), exclusive=True)

    def action_stop_conversation(self) -> None:
        self.session.stop()
        self._update_status("Gestoppt")
        self._update_controls()

    async def _start_session(self) -> None:
        self.is_busy = True
        self._update_status("Starte...")
        self._update_controls()
        try:
            greeting = await self.session.start()
            if not self.session.is_active:
                self._update_status("Gestoppt")
                return
            self.conversation_history.clear()
            if greeting:
                self._append_turn("assistant", greeting)
            self._update_status("Bereit")
        except Exception as e:
            self.session.stop()
            self.notify(f"Fehler: {e}", severity="error")
            self._update_status("Fehler")
        finally:
            self.is_busy = False
            self._update_controls()

    async def _process_turn(self) -> None:
        self.is_busy = True
        self._update_controls()
        try:
            self._update_status("Hören...")
            user_text = await self.session.listen()
            if not self.session.is_active:
                self._update_status("Gestoppt")
                return

            cleaned_user_text = user_text.strip()
            if not cleaned_user_text:
                self._update_status("Bereit")
                return

            self._append_turn("user", cleaned_user_text)
            self._update_status("Denken...")
            ai_response = await self.session.respond(cleaned_user_text)
            if not self.session.is_active:
                self._update_status("Gestoppt")
                return

            if ai_response:
                self._append_turn("assistant", ai_response)

            self._update_status("Sprechen...")
            await self.session.speak(ai_response)

            if self.session.is_active:
                self._update_status("Bereit")
            else:
                self._update_status("Gestoppt")
        except TimeoutError:
            self.notify("Keine Sprache erkannt - versuchen Sie es erneut", severity="warning")
            self._update_status("Bereit")
        except ValueError as e:
            self.notify(f"Erkennungsfehler: {e}", severity="warning")
            self._update_status("Bereit")
        except Exception as e:
            self.notify(f"Fehler: {e}", severity="error")
            self._update_status("Fehler")
        finally:
            self.is_busy = False
            self._update_controls()

    def _update_status(self, text: str = "Bereit") -> None:
        try:
            status = self.query_one("#status-bar", Static)
            status.update(f"Freies Gespräch | {text}")
        except Exception:
            pass

    def _append_turn(self, role: str, text: str) -> None:
        if not text.strip():
            return
        self.conversation_history.append(ConversationTurn(role=role, text=text.strip()))
        self._render_transcript()

    def _render_transcript(self) -> None:
        try:
            widget = self.query_one("#conversation-transcript", Static)
            if not self.conversation_history:
                widget.update("Noch kein Gespräch gestartet.")
                return

            lines: list[str] = []
            for turn in self.conversation_history:
                speaker = "Sie" if turn.role == "user" else "DeutschBuddy"
                prefix = "🗣️" if turn.role == "user" else "🤖"
                lines.append(f"{prefix} {speaker}: {turn.text}")
                lines.append("")
            widget.update("\n".join(lines).strip())
        except Exception:
            pass

    def _update_controls(self) -> None:
        try:
            start_button = self.query_one("#start-btn", Button)
            speak_button = self.query_one("#speak-btn", Button)
            stop_button = self.query_one("#stop-btn", Button)

            start_button.disabled = self.session.is_active or self.is_busy
            speak_button.disabled = (not self.session.is_active) or self.is_busy
            stop_button.disabled = not self.session.is_active
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            self.action_start_conversation()
        elif event.button.id == "speak-btn":
            self.action_capture_turn()
        elif event.button.id == "stop-btn":
            self.action_stop_conversation()
