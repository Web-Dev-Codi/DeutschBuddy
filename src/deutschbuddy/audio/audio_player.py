"""Non-blocking audio file playback using pygame."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

try:
    import pygame.mixer
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class AudioPlayer:
    """Handles non-blocking audio file playback.

    Uses pygame.mixer for cross-platform audio playback without blocking the UI.
    Falls back to dummy implementation if pygame is not available.
    """

    _initialized = False
    _lock = threading.Lock()

    def __init__(self) -> None:
        """Initialize the audio player."""
        if not PYGAME_AVAILABLE:
            return

        with AudioPlayer._lock:
            if not AudioPlayer._initialized:
                try:
                    pygame.mixer.init(frequency=22050, size=-16, channels=1)
                    AudioPlayer._initialized = True
                except pygame.error:
                    pass

    def play(self, audio_path: str | Path, on_complete: Callable[[], None] | None = None) -> bool:
        """Play an audio file without blocking.

        Args:
            audio_path: Path to the audio file (WAV or MP3)
            on_complete: Optional callback when playback finishes

        Returns:
            True if playback started successfully, False otherwise
        """
        if not PYGAME_AVAILABLE or not AudioPlayer._initialized:
            return False

        path = Path(audio_path)
        if not path.exists():
            return False

        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()

            if on_complete:
                threading.Thread(
                    target=self._wait_for_completion,
                    args=(on_complete,),
                    daemon=True,
                ).start()

            return True
        except pygame.error:
            return False

    def stop(self) -> None:
        """Stop any currently playing audio."""
        if not PYGAME_AVAILABLE or not AudioPlayer._initialized:
            return

        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        if not PYGAME_AVAILABLE or not AudioPlayer._initialized:
            return False

        try:
            return pygame.mixer.music.get_busy()
        except pygame.error:
            return False

    def _wait_for_completion(self, callback: Callable[[], None]) -> None:
        """Wait for playback to complete and trigger callback."""
        if not PYGAME_AVAILABLE:
            return

        try:
            while pygame.mixer.music.get_busy():
                pygame.time.wait(50)
            callback()
        except pygame.error:
            pass
