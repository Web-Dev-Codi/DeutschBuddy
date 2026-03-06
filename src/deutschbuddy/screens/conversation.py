"""Conversation screen with push-to-talk interface."""

from __future__ import annotations

import asyncio
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static
from textual.binding import Binding

from deutschbuddy.audio.listener import AudioListener
from deutschbuddy.audio.speaker import AudioSpeaker
from deutschbuddy.llm.conversation_agent import ConversationAgent
from deutschbuddy.models.lesson import CEFRLevel


class ConversationScreen(Screen):
    """Main conversation interface with push-to-talk."""
    
    BINDINGS = [
        Binding("space", "hold_to_talk", "Hold to Talk", show=False),
        Binding("l", "change_level", "Level"),
        Binding("m", "change_mode", "Mode"),
        Binding("t", "toggle_transcript", "Transcript"),
        Binding("q", "quit", "Quit"),
        Binding("escape", "close", "Close"),
    ]
    
    def __init__(
        self,
        listener: AudioListener,
        speaker: AudioSpeaker,
        conversation_agent: ConversationAgent,
    ):
        """Initialize conversation screen.
        
        Args:
            listener: Audio listener for STT
            speaker: Audio speaker for TTS
            conversation_agent: Conversation agent for AI responses
        """
        super().__init__()
        self.listener = listener
        self.speaker = speaker
        self.agent = conversation_agent
        self.is_recording = False
        self.transcript_visible = True
        self.conversation_history: list[tuple[str, str]] = []
        
    def compose(self) -> ComposeResult:
        """Compose the conversation UI."""
        yield Header()
        
        # Status bar
        yield Static(id="status-bar", classes="status-bar")
        
        # Main conversation area
        with Static(id="conversation-area"):
            # AI response area
            yield Static(id="ai-response", classes="response-area")
            
            # User input area
            yield Static(id="user-input", classes="input-area")
        
        # Record button (more reliable than space key detection)
        yield Button("🎤 RECORD", id="record-btn", variant="primary")
        
        # Instructions
        yield Static("🎤 Drücken Sie LEERTASTE oder RECORD zum Sprechen", id="instructions")
        
        yield Footer()
        
    def on_mount(self) -> None:
        """Initialize audio on mount."""
        try:
            self.listener.calibrate()
            self._update_status()
        except Exception as e:
            self.notify(f"Audio initialization error: {e}", severity="error")
            self._update_status("Audio Error")
        
    def action_hold_to_talk(self) -> None:
        """Handle push-to-talk interaction."""
        if self.is_recording:
            return
        
        self.is_recording = True
        self._update_status("Aufnahme...")
        
        # Process in worker thread
        self.run_worker(self._process_speech(), exclusive=True)
        
    async def _process_speech(self) -> None:
        """Worker task: Listen → Transcribe → Query AI → Speak."""
        try:
            # Step 1: Listen
            self._update_status("Hören...")
            user_text = await asyncio.to_thread(self.listener.listen, timeout=5)
            
            # Step 2: Display transcript
            self._update_user_text(user_text)
            
            # Step 3: Query AI
            self._update_status("Denken...")
            ai_response = await self.agent.chat(user_text)
            
            # Step 4: Speak response
            self._update_status("Sprechen...")
            await asyncio.to_thread(self.speaker.speak, ai_response)
            
            # Step 5: Update display
            self._update_ai_text(ai_response)
            self._update_status("Bereit")
            
            # Add to conversation history
            self.conversation_history.append((user_text, ai_response))
            
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
            self.is_recording = False
        
    def _update_status(self, text: str = "Bereit") -> None:
        """Update status bar."""
        try:
            status = self.query_one("#status-bar", Static)
            level = self.agent.level.value
            status.update(f"Level: {level} | {text}")
        except Exception:
            pass  # Widget might not be ready yet
    
    def _update_user_text(self, text: str) -> None:
        """Update user transcript."""
        try:
            widget = self.query_one("#user-input", Static)
            widget.update(f"🗣️ Sie: {text}")
        except Exception:
            pass
    
    def _update_ai_text(self, text: str) -> None:
        """Update AI response."""
        try:
            widget = self.query_one("#ai-response", Static)
            widget.update(f"🤖 AI: {text}")
        except Exception:
            pass
        
    def action_change_level(self) -> None:
        """Cycle through CEFR levels."""
        levels = [CEFRLevel.A1, CEFRLevel.A2, CEFRLevel.B1]
        current_idx = levels.index(self.agent.level)
        next_idx = (current_idx + 1) % len(levels)
        self.agent.set_level(levels[next_idx])
        self.set_speaker_rate_for_level(levels[next_idx])
        self.notify(f"Level: {levels[next_idx].value}")
        self._update_status()
    
    def set_speaker_rate_for_level(self, level: CEFRLevel) -> None:
        """Adjust TTS rate based on level."""
        rates = {CEFRLevel.A1: 120, CEFRLevel.A2: 150, CEFRLevel.B1: 170}
        self.speaker.set_rate(rates[level])
        
    def action_change_mode(self) -> None:
        """Cycle through conversation modes."""
        # Placeholder for future mode functionality
        self.notify("Mode change not implemented yet")
        
    def action_toggle_transcript(self) -> None:
        """Show/hide conversation transcript."""
        self.transcript_visible = not self.transcript_visible
        try:
            conversation_area = self.query_one("#conversation-area", Static)
            if self.transcript_visible:
                conversation_area.display = True
                self.notify("Transcript visible")
            else:
                conversation_area.display = False
                self.notify("Transcript hidden")
        except Exception:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "record-btn":
            self.action_hold_to_talk()
