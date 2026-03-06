"""Tests for AudioListener class."""

import pytest
from unittest.mock import Mock, patch
from deutschbuddy.audio.listener import AudioListener


def test_listener_init():
    """Test AudioListener initialization."""
    listener = AudioListener()
    assert listener.language == "de-DE"
    assert listener.model == "tiny"
    assert listener.microphone is not None  # Microphone is now initialized in __init__


@patch('speech_recognition.Recognizer')
@patch('speech_recognition.Microphone')
def test_listen_success(mock_mic, mock_recognizer):
    """Test successful speech recognition."""
    # Setup mocks
    mock_recognizer_instance = Mock()
    mock_recognizer.return_value = mock_recognizer_instance
    mock_recognizer_instance.recognize_whisper.return_value = "Guten Tag"
    
    listener = AudioListener()
    listener.microphone = mock_mic.return_value
    
    result = listener.listen(timeout=1)
    assert result == "Guten Tag"


@patch('speech_recognition.Recognizer')
@patch('speech_recognition.Microphone')
def test_listen_timeout(mock_mic, mock_recognizer):
    """Test timeout handling."""
    import speech_recognition as sr
    
    mock_recognizer_instance = Mock()
    mock_recognizer.return_value = mock_recognizer_instance
    mock_recognizer_instance.listen.side_effect = sr.WaitTimeoutError("timeout")
    
    listener = AudioListener()
    listener.microphone = mock_mic.return_value
    
    with pytest.raises(TimeoutError):
        listener.listen(timeout=1)


@patch('speech_recognition.Recognizer')
@patch('speech_recognition.Microphone')
def test_listen_not_recognized(mock_mic, mock_recognizer):
    """Test speech not recognized error."""
    import speech_recognition as sr
    
    mock_recognizer_instance = Mock()
    mock_recognizer.return_value = mock_recognizer_instance
    mock_recognizer_instance.recognize_whisper.side_effect = sr.UnknownValueError("not recognized")
    
    listener = AudioListener()
    listener.microphone = mock_mic.return_value
    
    with pytest.raises(ValueError):
        listener.listen(timeout=1)


@patch('speech_recognition.Microphone')
def test_microphone_detection(mock_mic_class):
    """Test microphone device detection."""
    mock_mic_class.list_microphone_names.return_value = ["Default Mic", "USB Mic"]
    
    listener = AudioListener()
    device = listener.get_microphone_device()
    
    assert device == 0
    mock_mic_class.list_microphone_names.assert_called_once()


@patch('speech_recognition.Microphone')
def test_no_microphone_detected(mock_mic_class):
    """Test error when no microphone found."""
    mock_mic_class.list_microphone_names.return_value = []
    
    listener = AudioListener()
    
    with pytest.raises(RuntimeError, match="No microphone detected"):
        listener.get_microphone_device()


@patch('speech_recognition.Microphone')
@patch('speech_recognition.Recognizer')
def test_calibrate(mock_recognizer_class, mock_mic_class):
    """Test ambient noise calibration."""
    mock_mic_instance = Mock()
    mock_mic_instance.__enter__ = Mock(return_value=mock_mic_instance)
    mock_mic_instance.__exit__ = Mock(return_value=None)
    mock_mic_class.return_value = mock_mic_instance
    mock_recognizer_instance = Mock()
    mock_recognizer_class.return_value = mock_recognizer_instance
    
    listener = AudioListener()
    listener.calibrate(duration=0.5)
    
    mock_recognizer_instance.adjust_for_ambient_noise.assert_called_once_with(
        mock_mic_instance, duration=0.5
    )


@patch('speech_recognition.Microphone')
@patch('speech_recognition.Recognizer')
def test_pyaudio_fd_error_recovery(mock_recognizer_class, mock_mic_class):
    """Test recovery from PyAudio file descriptor error."""
    mock_recognizer_instance = Mock()
    mock_recognizer_class.return_value = mock_recognizer_instance
    
    # First call raises the fd error, second call succeeds
    mock_mic_instance = Mock()
    mock_mic_instance.__enter__ = Mock(return_value=mock_mic_instance)
    mock_mic_instance.__exit__ = Mock(return_value=None)
    mock_mic_class.side_effect = [
        OSError("bad value(s) in fds_to_keep"),  # First call fails
        mock_mic_instance  # Second call succeeds
    ]
    
    listener = AudioListener()
    
    # Should handle the error and retry successfully
    assert listener.microphone is not None
