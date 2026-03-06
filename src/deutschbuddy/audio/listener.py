"""Handles microphone input and speech-to-text transcription."""

import speech_recognition as sr


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
        self._init_microphone()
        
    def _init_microphone(self) -> None:
        """Initialize microphone with robust error handling."""
        try:
            self.microphone = sr.Microphone()
        except OSError as e:
            if "bad value(s) in fds_to_keep" in str(e):
                # Try with explicit device index
                try:
                    device_index = self.get_microphone_device()
                    self.microphone = sr.Microphone(device_index=device_index)
                except Exception:
                    # Last resort - try without any parameters
                    self.microphone = sr.Microphone()
            else:
                raise
        
    def listen(self, timeout: int = 5) -> str:
        """Listen for speech and return transcribed text.
        
        Args:
            timeout: Maximum seconds to wait for speech
            
        Returns:
            Transcribed German text
            
        Raises:
            TimeoutError: If no speech detected within timeout
            ValueError: If speech not recognized
            RuntimeError: If Whisper engine fails
        """
        if self.microphone is None:
            self.microphone = sr.Microphone()
            
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=timeout)
        except sr.WaitTimeoutError:
            raise TimeoutError("No speech detected within timeout period")
        except OSError as e:
            if "bad value(s) in fds_to_keep" in str(e):
                # Handle PyAudio file descriptor issue
                # Reinitialize microphone and try again
                self.microphone = None
                return self.listen(timeout)
            else:
                raise RuntimeError(f"Microphone error: {e}")
        
        try:
            # Use Whisper for offline recognition
            text = self.recognizer.recognize_whisper(
                audio,
                language="de",
                model=self.model,
            )
            return text.strip()
        except sr.UnknownValueError:
            raise ValueError("Speech not recognized - try again")
        except sr.RequestError as e:
            raise RuntimeError(f"Whisper error: {e}")
        
    def calibrate(self, duration: float = 1.0) -> None:
        """Adjust for ambient noise levels.
        
        Args:
            duration: Seconds to sample ambient noise
        """
        if self.microphone is None:
            self.microphone = sr.Microphone()
            
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
        except OSError as e:
            if "bad value(s) in fds_to_keep" in str(e):
                # Reinitialize microphone and retry calibration
                self.microphone = None
                self.calibrate(duration)
            else:
                raise RuntimeError(f"Microphone calibration error: {e}")
        
    def get_microphone_device(self) -> int:
        """Auto-detect default microphone device index.
        
        Returns:
            Device index for microphone
            
        Raises:
            RuntimeError: If no microphone detected
        """
        mics = sr.Microphone.list_microphone_names()
        if not mics:
            raise RuntimeError("No microphone detected")
        # Return default or first available
        return 0
