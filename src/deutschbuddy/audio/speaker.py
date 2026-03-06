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
        self.engine.say(text)
        self.engine.runAndWait()
        
    def get_available_voices(self) -> list[dict]:
        """Get list of available TTS voices.
        
        Returns:
            List of voice dicts with id, name, languages
        """
        voices = []
        for voice in self.engine.getProperty('voices'):
            voices.append({
                'id': voice.id,
                'name': voice.name,
                'languages': voice.languages or [],
                'gender': voice.gender,
            })
        return voices
        
    def set_rate(self, wpm: int) -> None:
        """Set speech rate for learner level.
        
        Args:
            wpm: Words per minute (A1: 120, A2: 150, B1: 170)
        """
        self.rate = wpm
        self.engine.setProperty('rate', wpm)
        
    def _configure_german_voice(self) -> None:
        """Configure German voice from espeak-ng."""
        voices = self.engine.getProperty('voices')
        german_voice = None
        
        for voice in voices:
            # Check for German language codes or German in name
            if (voice.languages and 
                any('de' in str(lang).lower() for lang in voice.languages)):
                german_voice = voice.id
                break
            elif 'german' in voice.name.lower() or 'deutsch' in voice.name.lower():
                german_voice = voice.id
                break
        
        if german_voice:
            self.engine.setProperty('voice', german_voice)
        else:
            # Fallback - try to set voice by language code
            try:
                self.engine.setProperty('voice', 'de')
            except (ValueError, RuntimeError):
                pass  # Use default voice if German not available
        
        self.engine.setProperty('rate', self.rate)
