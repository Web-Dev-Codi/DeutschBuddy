"""Handles microphone input and speech-to-text transcription."""

import os
import speech_recognition as sr
try:  # Optional: use PyAudio directly to pick a valid input device
    import pyaudio  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    pyaudio = None  # fallback to SR's default device selection


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
            # Prefer a valid input-capable device if PyAudio is available
            device_index = None

            # Allow explicit override via env (index or substring of device name)
            env_dev = os.getenv("DEUTSCHBUDDY_INPUT_DEVICE")
            if env_dev:
                try:
                    device_index = int(env_dev)
                except ValueError:
                    try:
                        names = sr.Microphone.list_microphone_names()
                        low = env_dev.lower()
                        for i, name in enumerate(names):
                            if low in str(name).lower():
                                device_index = i
                                break
                    except Exception:
                        device_index = None

            if pyaudio is not None and device_index is None:
                try:
                    pa = pyaudio.PyAudio()
                    try:
                        # Try the system default input device first
                        try:
                            info = pa.get_default_input_device_info()
                            if info and info.get("maxInputChannels", 0) > 0:
                                device_index = int(info.get("index", 0))
                        except Exception:
                            # No default input; scan for first input-capable device
                            for i in range(pa.get_device_count()):
                                di = pa.get_device_info_by_index(i)
                                if di.get("maxInputChannels", 0) > 0:
                                    device_index = int(di.get("index", i))
                                    break
                    finally:
                        pa.terminate()
                except Exception:
                    device_index = None

            self.microphone = sr.Microphone(device_index=device_index)
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
        
    def listen(self, timeout: int = 5, _retry: bool = False) -> str:
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
        except AttributeError as e:
            # Some backends may leave stream None and __exit__ tries to close it
            if "close" in str(e):
                # Reinitialize and retry once
                self._init_microphone()
                if not _retry:
                    return self.listen(timeout, _retry=True)
                raise RuntimeError("Microphone stream error after retry") from e
            raise
        except OSError as e:
            if "bad value(s) in fds_to_keep" in str(e):
                # Handle PyAudio file descriptor issue
                # Reinitialize microphone and try again
                self.microphone = None
                if not _retry:
                    return self.listen(timeout, _retry=True)
                raise RuntimeError("Microphone backend error after retry") from e
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
        except OSError as e:
            # Catch low-level decoder or device-related OSErrors that may surface here
            if "bad value(s) in fds_to_keep" in str(e):
                # Reinitialize mic and hint to user-space configuration
                self._init_microphone()
                raise RuntimeError("Audio backend error while decoding audio. Try selecting a specific input device or fixing ALSA/PipeWire setup.") from e
            raise
        
    def calibrate(self, duration: float = 1.0, _retry: bool = False) -> None:
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
                if not _retry:
                    self.calibrate(duration, _retry=True)
                    return
                # Final fallback: skip calibration but keep app usable
                return
            else:
                # Non-fd errors: try re-init once, then skip
                if not _retry:
                    self._init_microphone()
                    self.calibrate(duration, _retry=True)
                    return
                return
        except AttributeError as e:
            if "close" in str(e):
                self._init_microphone()
                if not _retry:
                    self.calibrate(duration, _retry=True)
                    return
                # Final fallback: skip calibration to avoid blocking UX
                return
            # Unknown attribute error: do not crash init
            return
        
    def get_microphone_device(self) -> int:
        """Auto-detect default microphone device index.
        
        Returns:
            Device index for microphone
            
        Raises:
            RuntimeError: If no microphone detected
        """
        # Env override first (index or substring)
        env_dev = os.getenv("DEUTSCHBUDDY_INPUT_DEVICE")
        if env_dev:
            try:
                return int(env_dev)
            except ValueError:
                names = sr.Microphone.list_microphone_names()
                low = env_dev.lower()
                for i, name in enumerate(names):
                    if low in str(name).lower():
                        return i

        # Fast path via SpeechRecognition listing
        mics = sr.Microphone.list_microphone_names()
        if not mics:
            raise RuntimeError("No microphone detected")

        # If PyAudio is present, prefer the first input-capable device
        if pyaudio is not None:
            try:
                pa = pyaudio.PyAudio()
                try:
                    try:
                        info = pa.get_default_input_device_info()
                        if info and info.get("maxInputChannels", 0) > 0:
                            return int(info.get("index", 0))
                    except Exception:
                        for i in range(pa.get_device_count()):
                            di = pa.get_device_info_by_index(i)
                            if di.get("maxInputChannels", 0) > 0:
                                return int(di.get("index", i))
                finally:
                    pa.terminate()
            except Exception:
                pass

        # Fallback to SR's index 0 (may map to default in many setups)
        return 0
