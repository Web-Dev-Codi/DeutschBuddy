# Voice Conversation Feature Design

**Date:** 2026-03-06  
**Status:** Proposed  
**Author:** deutschbuddy team

---

## Overview

Add a real-time voice conversation feature to DeutschBuddy that enables learners to practice German speaking with AI. The feature uses a push-to-talk interaction model with fully offline speech recognition and synthesis.

**Core Requirements:**
- ✅ Push-to-talk (press SPACE to record, release to process)
- ✅ Fully offline (Whisper for STT, pyttsx3/espeak for TTS)
- ✅ German TTS voice (espeak-ng `de-DE`)
- ✅ New TUI screen integrated into existing app

---

## Architecture

### Pipeline Flow

```
User presses SPACE → Listen → Transcribe (Whisper) → Query Ollama → Synthesize (pyttsx3) → Play
```

### System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    TUI Conversation Screen                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Press SPACE to record]                                     │
│         ↓                                                    │
│  ┌──────────────────┐                                        │
│  │  SpeechRecognition│  (Microphone input)                    │
│  │  + Whisper       │  (Offline STT)                         │
│  └──────────────────┘                                        │
│         ↓                                                    │
│  ┌──────────────────┐                                        │
│  │   OllamaClient   │  (German conversation AI)              │
│  └──────────────────┘                                        │
│         ↓                                                    │
│  ┌──────────────────┐                                        │
│  │    pyttsx3       │  (Text-to-Speech)                      │
│  └──────────────────┘                                        │
│         ↓                                                    │
│  [Audio Playback]                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Audio Module (`src/deutschbuddy/audio/`)

#### `listener.py` - Speech-to-Text

```python
"""Handles microphone input and speech-to-text transcription."""

import speech_recognition as sr
from pathlib import Path


class AudioListener:
    """Handles microphone input and speech-to-text transcription."""
    
    def __init__(self, language: str = "de-DE", model: str = "tiny"):
        """Initialize the audio listener.
        
        Args:
            language: Language code for speech recognition (default: German)
            model: Whisper model size: tiny, base, small, medium, large
        """
        self.recognizer = sr.Recognizer()
        self.language = language
        self.model = model
        self.microphone = None
        
    def listen(self, timeout: int = 5) -> str:
        """Listen for speech and return transcribed text.
        
        Args:
            timeout: Maximum seconds to wait for speech
            
        Returns:
            Transcribed German text
            
        Raises:
            TimeoutError: If no speech detected within timeout
            UnknownValueError: If speech not recognized
        """
        pass
        
    def calibrate(self, duration: float = 1.0) -> None:
        """Adjust for ambient noise levels.
        
        Args:
            duration: Seconds to sample ambient noise
        """
        pass
        
    def get_microphone_device(self) -> int:
        """Auto-detect default microphone device index.
        
        Returns:
            Device index for microphone
        """
        pass
```

#### `speaker.py` - Text-to-Speech

```python
"""Handles text-to-speech synthesis with German voice."""

import pyttsx3


class AudioSpeaker:
    """Handles text-to-speech synthesis with German voice."""
    
    def __init__(self, voice: str = "de-DE", rate: int = 150):
        """Initialize the audio speaker.
        
        Args:
            voice: Voice ID (default: German)
            rate: Speech rate in words per minute
        """
        self.engine = pyttsx3.init()
        self.voice = voice
        self.rate = rate
        self._configure_german_voice()
        
    def speak(self, text: str) -> None:
        """Synthesize and play speech. Blocks until audio finishes.
        
        Args:
            text: German text to synthesize
        """
        pass
        
    def get_available_voices(self) -> list[dict]:
        """Get list of available TTS voices.
        
        Returns:
            List of voice dicts with id, name, languages
        """
        pass
        
    def set_rate(self, wpm: int) -> None:
        """Set speech rate for learner level.
        
        Args:
            wpm: Words per minute (A1: 120, A2: 150, B1: 170)
        """
        pass
        
    def _configure_german_voice(self) -> None:
        """Configure German voice from espeak-ng."""
        pass
```

---

### 2. Conversation Agent (`src/deutschbuddy/llm/conversation_agent.py`)

```python
"""Manages German conversation context with Ollama."""

from ollama import AsyncClient
fromdeutschbuddy.curriculum.cefr import CEFRLevel


SYSTEM_PROMPTS = {
    "A1": """Du bist ein deutscher Sprachlehrer für Anfänger.
Antworte auf Deutsch, verwende sehr einfache Sätze.
Benutze grundlegenden Wortschatz und Präsens.
Korrigiere höflich Fehler am Ende deiner Antwort.""",

    "A2": """Du bist ein deutscher Sprachlehrer.
Antworte auf Deutsch, verwende einfache Sätze.
Benutze Perfekt und Modalverben.
Korrigiere höflich Fehler am Ende deiner Antwort.""",

    "B1": """Du bist ein deutscher Sprachlehrer für fortgeschrittene Lerner.
Antworte auf Deutsch mit natürlichem Tempo.
Verwende komplexe Sätze, Konjunktiv II und Passiv.
Korrigiere Fehler am Ende deiner Antwort.""",
}


class ConversationAgent:
    """Manages German conversation context with Ollama."""
    
    def __init__(
        self,
        ollama_client: AsyncClient,
        model: str = "mistral:7b-instruct",
        level: CEFRLevel = CEFRLevel.A1,
    ):
        """Initialize the conversation agent.
        
        Args:
            ollama_client: Ollama async client
            model: Model name for conversation
            level: CEFR proficiency level
        """
        self.client = ollama_client
        self.model = model
        self.level = level
        self.history: list[dict] = []
        
    async def chat(self, message: str) -> str:
        """Send message and receive AI response.
        
        Args:
            message: User's German text
            
        Returns:
            AI response in German
        """
        pass
        
    def set_level(self, level: CEFRLevel) -> None:
        """Adjust conversation difficulty level.
        
        Args:
            level: New CEFR level
        """
        pass
        
    def get_correction(self, user_text: str, ai_response: str) -> str:
        """Get grammar/vocabulary feedback on user input.
        
        Args:
            user_text: User's original text
            ai_response: AI's response
            
        Returns:
            Correction feedback in English/German
        """
        pass
        
    def clear_history(self) -> None:
        """Clear conversation history."""
        pass
```

---

### 3. TUI Conversation Screen (`src/deutschbuddy/screens/conversation.py`)

```python
"""Conversation screen with push-to-talk interface."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Button
from textual.binding import Binding

from deutschbuddy.audio.listener import AudioListener
from deutschbuddy.audio.speaker import AudioSpeaker
from deutschbuddy.llm.conversation_agent import ConversationAgent
from deutschbuddy.curriculum.cefr import CEFRLevel


class ConversationScreen(Screen):
    """Main conversation interface with push-to-talk."""
    
    BINDINGS = [
        Binding("space", "hold_to_talk", "Hold to Talk", show=False),
        Binding("l", "change_level", "Level"),
        Binding("m", "change_mode", "Mode"),
        Binding("t", "toggle_transcript", "Transcript"),
        Binding("q", "quit", "Quit"),
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
        yield Label(id="status-bar", classes="status-bar")
        
        # AI response area
        yield Label(id="ai-response", classes="response-area")
        
        # User input area
        yield Label(id="user-input", classes="input-area")
        
        # Instructions
        yield Label(id="instructions", classes="instructions")
        
        yield Footer()
        
    def on_mount(self) -> None:
        """Initialize audio on mount."""
        self.listener.calibrate()
        self._update_status()
        
    def action_hold_to_talk(self) -> None:
        """Handle push-to-talk interaction."""
        # This will be implemented with key press/release handling
        pass
        
    async def _process_speech(self) -> None:
        """Worker task: Listen → Transcribe → Query AI → Speak."""
        pass
        
    def _update_status(self) -> None:
        """Update status bar with current level and mode."""
        pass
        
    def _update_transcript(self, user_text: str, ai_response: str) -> None:
        """Add exchange to transcript display."""
        self.conversation_history.append((user_text, ai_response))
        pass
        
    def action_change_level(self) -> None:
        """Cycle through CEFR levels."""
        pass
        
    def action_change_mode(self) -> None:
        """Cycle through conversation modes."""
        pass
        
    def action_toggle_transcript(self) -> None:
        """Show/hide conversation transcript."""
        pass
```

---

## Data Flow

```
1. User presses and holds SPACE
   ↓
2. AudioListener.listen(timeout=5) → audio_data
   ↓
3. SpeechRecognition.recognize_whisper(audio_data, language="de-DE")
   ↓
4. German text: "Guten Tag, wie geht es dir?"
   ↓
5. ConversationAgent.chat(user_text, conversation_history)
   ↓
6. AI response: "Mir geht es gut! Und Ihnen?"
   ↓
7. AudioSpeaker.speak(ai_response)
   ↓
8. Audio plays through system speakers
   ↓
9. Update transcript display
   ↓
10. Loop back to listening state
```

---

## Error Handling

| Error Type | Handling Strategy | User Feedback |
|------------|------------------|---------------|
| Microphone not found | Fallback to text input | "🎤 No mic detected - check Settings" |
| Whisper timeout | Retry 2x, then show message | "🤔 Didn't catch that - try again?" |
| Ollama unavailable | Queue message, notify | "🦙 Ollama not running" |
| TTS engine failure | Display text only | Show transcript on screen |
| Background noise | Calibrate on startup | "Calibrating..." indicator |

---

## Dependencies

### Python Packages (pyproject.toml)

```toml
[dependency-groups]
voice = [
  "SpeechRecognition>=3.14.0",
  "PyAudio>=0.2.11",
  "pyttsx3>=2.90",
  "openai-whisper>=20231117",
]
```

Install: `uv sync --extra voice`

### System Dependencies

```bash
# Ubuntu/Debian (AMD ROCm setup)
sudo apt-get install:
  - espeak-ng          # TTS engine (German voices)
  - espeak-ng-de       # German language pack
  - portaudio19-dev    # PyAudio requirement
  - python3-pyaudio    # Microphone access
```

### Whisper Model

Downloaded automatically on first run. Options:
- `tiny` (fastest, ~100MB) - Recommended for real-time
- `base` (moderate, ~150MB)
- `small` (accurate, ~500MB)
- `medium` (best, ~1.5GB)

---

## CEFR Level Adjustments

| Level | AI Behavior | TTS Rate (WPM) | Vocabulary |
|-------|-------------|----------------|------------|
| A1 | Short sentences, basic vocab, Präsens only | 120 | Greetings, numbers, colors |
| A2 | Simple past/present, Modalverben, everyday topics | 150 | Family, food, daily routine |
| B1 | Complex sentences, Konjunktiv II, Passiv | 170 | Travel, work, opinions |

---

## File Structure

```
src/deutschbuddy/
├── audio/
│   ├── __init__.py
│   ├── listener.py          # Speech-to-Text
│   └── speaker.py           # Text-to-Speech
├── llm/
│   ├── conversation_agent.py  # Conversation management
│   └── prompts.py           # Add conversation prompts
├── screens/
│   └── conversation.py      # Voice conversation screen
└── main.py                  # Add conversation route
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_audio_listener.py
- test_listen_german_phrase()
- test_calibrate_silence()
- test_microphone_detection()
- test_timeout_error()

# tests/test_audio_speaker.py
- test_german_voice_selection()
- test_speak_blocks()
- test_available_voices_contains_de()
- test_rate_adjustment()

# tests/test_conversation_agent.py
- test_german_response()
- test_level_adjustment()
- test_correction_feedback()
- test_history_management()
```

### Integration Tests

```python
# tests/test_conversation_flow.py
- test_full_pipeline_push_to_talk()
- test_level_change_mid_conversation()
- test_error_recovery_no_microphone()
```

---

## Future Enhancements (Post-MVP)

1. **Barge-in Detection** - Interrupt AI mid-sentence
2. **Voice Activity Detection** - Auto-end recording on silence
3. **Streaming TTS** - Play audio as generated (lower latency)
4. **Multiple Voices** - Choose male/female AI voice
5. **Conversation History** - Review and export past sessions
6. **Pronunciation Feedback** - AI critiques user's German accent
7. **Recording** - Save conversation audio for review
8. **Offline LLM** - Full offline mode with local model

---

## References

- [SpeechRecognition Library](https://pypi.org/project/SpeechRecognition/)
- [Whisper Documentation](https://github.com/openai/whisper)
- [pyttsx3 Documentation](https://pyttsx3.readthedocs.io/)
- [Ollama Python Client](https://github.com/ollama/ollama-python)
- [local-voice GitHub](https://github.com/Robin-07/local-voice) - Reference implementation
- [espeak-ng Voices](https://github.com/espeak-ng/espeak-ng) - German voice data

---

## Appendix: Example Conversation

```
AI:  Guten Tag! Wie heißen Sie?
You: Guten Tag! Ich heiße Thomas.
AI:  Freut mich, Thomas! Woher kommen Sie?
You:  Ich komme aus den USA. Und Sie?
AI:  Ich komme aus Deutschland. Ich bin aus Berlin.
     (Correction: "Sie" is formal - good! Keep using it.)
You:  Was machen Sie in Ihrer Freizeit?
AI:  Ich lese gerne Bücher und koche. Und Sie?
```

---

*Document Version: 1.0*  
*Last Updated: 2026-03-06*
