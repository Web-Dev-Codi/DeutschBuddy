"""Audio module for speech recognition and synthesis."""

from deutschbuddy.audio.audio_player import AudioPlayer
from deutschbuddy.audio.listener import AudioListener
from deutschbuddy.audio.pronunciation_service import PronunciationService
from deutschbuddy.audio.speaker import AudioSpeaker
from deutschbuddy.audio.wiktionary_client import WiktionaryClient

__all__ = [
    "AudioListener",
    "AudioPlayer",
    "AudioSpeaker",
    "PronunciationService",
    "WiktionaryClient",
]
