"""Non-blocking audio file playback using pygame."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import warnings
from pathlib import Path
from typing import Callable

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
warnings.filterwarnings(
    "ignore",
    message=r"Your system is avx2 capable but pygame was not built with support for it.*",
    category=RuntimeWarning,
)

try:
    import pygame.mixer
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


LOGGER = logging.getLogger(__name__)
FFPLAY_PATH = shutil.which("ffplay")


class AudioPlayer:
    """Handles non-blocking audio file playback.

    Uses pygame.mixer for cross-platform audio playback without blocking the UI.
    Falls back to dummy implementation if pygame is not available.
    """

    _initialized = False
    _lock = threading.Lock()
    _last_error: str | None = None
    _backend = "none"
    _process: subprocess.Popen[bytes] | None = None

    def __init__(self) -> None:
        """Initialize the audio player."""
        with AudioPlayer._lock:
            if AudioPlayer._backend in {"pygame", "ffplay"}:
                return

            if not PYGAME_AVAILABLE:
                if FFPLAY_PATH:
                    AudioPlayer._backend = "ffplay"
                    AudioPlayer._last_error = None
                else:
                    AudioPlayer._last_error = "Neither pygame.mixer nor ffplay is available"
                return

            if not AudioPlayer._initialized:
                try:
                    pygame.mixer.init(frequency=22050, size=-16, channels=1)
                    AudioPlayer._initialized = True
                    AudioPlayer._backend = "pygame"
                    AudioPlayer._last_error = None
                except pygame.error as exc:
                    if FFPLAY_PATH:
                        AudioPlayer._backend = "ffplay"
                        AudioPlayer._last_error = None
                        LOGGER.warning("pygame mixer init failed: %s; falling back to ffplay", exc)
                    else:
                        AudioPlayer._last_error = f"pygame mixer init failed: {exc}"
                        LOGGER.warning("%s", AudioPlayer._last_error)

    def is_available(self) -> bool:
        return AudioPlayer._backend in {"pygame", "ffplay"}

    def last_error(self) -> str | None:
        return AudioPlayer._last_error

    def play(self, audio_path: str | Path, on_complete: Callable[[], None] | None = None) -> bool:
        """Play an audio file without blocking.

        Args:
            audio_path: Path to the audio file (WAV or MP3)
            on_complete: Optional callback when playback finishes

        Returns:
            True if playback started successfully, False otherwise
        """
        if not self.is_available():
            if AudioPlayer._last_error is None:
                AudioPlayer._last_error = "pygame mixer is unavailable"
            return False

        path = Path(audio_path)
        if not path.exists():
            AudioPlayer._last_error = f"audio file not found: {path}"
            return False

        if AudioPlayer._backend == "ffplay":
            return self._play_with_ffplay(path, on_complete)

        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()
            AudioPlayer._last_error = None

            if on_complete:
                threading.Thread(
                    target=self._wait_for_completion,
                    args=(on_complete,),
                    daemon=True,
                ).start()

            return True
        except pygame.error as exc:
            AudioPlayer._last_error = f"pygame playback failed: {exc}"
            LOGGER.warning("%s", AudioPlayer._last_error)
            return False

    def stop(self) -> None:
        """Stop any currently playing audio."""
        if not self.is_available():
            return

        if AudioPlayer._backend == "ffplay":
            self._stop_ffplay()
            return

        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        if not self.is_available():
            return False

        if AudioPlayer._backend == "ffplay":
            process = AudioPlayer._process
            return process is not None and process.poll() is None

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

    def _play_with_ffplay(self, audio_path: Path, on_complete: Callable[[], None] | None = None) -> bool:
        self._stop_ffplay()

        if not FFPLAY_PATH:
            AudioPlayer._last_error = "ffplay is not available"
            return False

        try:
            process = subprocess.Popen(
                [FFPLAY_PATH, "-nodisp", "-autoexit", "-loglevel", "error", str(audio_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            AudioPlayer._last_error = f"ffplay start failed: {exc}"
            LOGGER.warning("%s", AudioPlayer._last_error)
            return False

        AudioPlayer._process = process
        AudioPlayer._last_error = None

        if on_complete:
            threading.Thread(
                target=self._wait_for_process_completion,
                args=(process, on_complete),
                daemon=True,
            ).start()

        return True

    def _stop_ffplay(self) -> None:
        process = AudioPlayer._process
        if process is None:
            return

        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)

        AudioPlayer._process = None

    def _wait_for_process_completion(
        self,
        process: subprocess.Popen[bytes],
        callback: Callable[[], None],
    ) -> None:
        try:
            process.wait()
        except Exception:
            return

        if AudioPlayer._process is process:
            AudioPlayer._process = None

        if process.returncode == 0:
            callback()
