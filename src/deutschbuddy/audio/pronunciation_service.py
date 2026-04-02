"""Pronunciation service with three-tier fallback: Wiktionary → Forvo → Piper TTS."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

from deutschbuddy.audio.audio_player import AudioPlayer
from deutschbuddy.audio.wiktionary_client import WiktionaryClient


class PronunciationService:
    """Manages German word pronunciation with fallback chain.

    Priority order:
    1. Wiktionary (human recordings, cached)
    2. Forvo (native speaker recordings) - placeholder for future
    3. Piper TTS (local neural synthesis) - placeholder for future

    All audio is played through AudioPlayer for non-blocking playback.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize the pronunciation service.

        Args:
            cache_dir: Directory to cache downloaded/generated audio.
                      Defaults to ~/.cache/deutschbuddy/audio
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "deutschbuddy" / "audio"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._player = AudioPlayer()
        self._wiktionary = WiktionaryClient(cache_dir=self.cache_dir)

        self._current_word: str | None = None
        self._lock = threading.Lock()

    def play_pronunciation(
        self,
        word: str,
        on_complete: Callable[[], None] | None = None,
    ) -> bool:
        """Play pronunciation for a German word with fallback chain.

        Args:
            word: German word to pronounce
            on_complete: Optional callback when playback finishes

        Returns:
            True if audio playback was started (or will be attempted),
            False if all sources failed
        """
        if not word or not word.strip():
            return False

        word = word.strip()

        with self._lock:
            self._stop_current()
            self._current_word = word

        threading.Thread(
            target=self._fetch_and_play,
            args=(word, on_complete),
            daemon=True,
        ).start()

        return True

    def replay(self, on_complete: Callable[[], None] | None = None) -> bool:
        """Replay the current word's pronunciation.

        Args:
            on_complete: Optional callback when playback finishes

        Returns:
            True if replay was started, False if no current word
        """
        with self._lock:
            word = self._current_word

        if not word:
            return False

        return self._play_cached_or_fetch(word, on_complete)

    def stop(self) -> None:
        """Stop any currently playing pronunciation."""
        with self._lock:
            self._stop_current()
            self._current_word = None

    def is_playing(self) -> bool:
        """Check if pronunciation is currently playing."""
        return self._player.is_playing()

    def _stop_current(self) -> None:
        """Stop current playback internally (must hold lock)."""
        self._player.stop()

    def _fetch_and_play(
        self,
        word: str,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Fetch pronunciation from available sources and play.

        Args:
            word: German word to pronounce
            on_complete: Optional callback when playback finishes
        """
        audio_path = self._get_cached_path(word)

        if audio_path.exists():
            self._play_file(audio_path, on_complete)
            return

        audio_path = self._wiktionary.fetch_audio(word)
        if audio_path and audio_path.exists():
            self._play_file(audio_path, on_complete)
            return

        audio_path = self._synthesize_with_piper(word)
        if audio_path and audio_path.exists():
            self._play_file(audio_path, on_complete)
            return

    def _play_cached_or_fetch(
        self,
        word: str,
        on_complete: Callable[[], None] | None = None,
    ) -> bool:
        """Play from cache if available, otherwise fetch and play.

        Args:
            word: German word to pronounce
            on_complete: Optional callback when playback finishes

        Returns:
            True if playback started, False otherwise
        """
        audio_path = self._get_cached_path(word)

        if audio_path.exists():
            self._play_file(audio_path, on_complete)
            return True

        threading.Thread(
            target=self._fetch_and_play,
            args=(word, on_complete),
            daemon=True,
        ).start()
        return True

    def _get_cached_path(self, word: str) -> Path:
        """Get the cache file path for a word.

        Tries multiple formats in order: .ogg (Wiktionary), .wav (Piper), .mp3

        Args:
            word: German word

        Returns:
            Path to potential cached audio file
        """
        safe_word = "".join(c if c.isalnum() or c == "-" else "_" for c in word.lower())

        for ext in [".ogg", ".wav", ".mp3"]:
            path = self.cache_dir / f"{safe_word}{ext}"
            if path.exists():
                return path

        return self.cache_dir / f"{safe_word}.ogg"

    def _play_file(
        self,
        audio_path: Path,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Play an audio file through the player.

        Args:
            audio_path: Path to audio file
            on_complete: Optional callback when playback finishes
        """
        def wrapped_callback() -> None:
            if on_complete:
                on_complete()

        self._player.play(audio_path, wrapped_callback)

    def _synthesize_with_piper(self, word: str) -> Path | None:
        """Synthesize pronunciation using Piper TTS.

        Args:
            word: German word to synthesize

        Returns:
            Path to synthesized audio file, or None on failure
        """
        try:
            from piper import PiperVoice

            output_path = self._get_cached_path(word)
            output_path = output_path.with_suffix(".wav")

            if output_path.exists():
                return output_path

            model_name = "de_DE-thorsten-medium.onnx"

            try:
                voice = PiperVoice.load(model_name, use_cuda=False)
            except Exception:
                return None

            import wave

            with wave.open(str(output_path), "wb") as wav_file:
                voice.synthesize(
                    text=word,
                    wav_file=wav_file,
                    speaker_id=None,
                    length_scale=1.0,
                    noise_scale=0.667,
                    noise_w=0.8,
                    sentence_silence=0.2,
                )

            return output_path if output_path.exists() else None
        except Exception:
            return None
