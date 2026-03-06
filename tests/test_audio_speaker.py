"""Tests for AudioSpeaker class."""

from unittest.mock import Mock, patch
from deutschbuddy.audio.speaker import AudioSpeaker


@patch('pyttsx3.init')
def test_speaker_init(mock_init):
    """Test AudioSpeaker initialization."""
    mock_engine = Mock()
    mock_engine.getProperty.return_value = []  # Return empty list for voices
    mock_init.return_value = mock_engine
    
    speaker = AudioSpeaker()
    
    assert speaker.voice == "de-DE"
    assert speaker.rate == 150
    mock_init.assert_called_once()


@patch('pyttsx3.init')
def test_speaker_init_custom(mock_init):
    """Test AudioSpeaker initialization with custom parameters."""
    mock_engine = Mock()
    mock_engine.getProperty.return_value = []  # Return empty list for voices
    mock_init.return_value = mock_engine
    
    speaker = AudioSpeaker(voice="custom", rate=200)
    
    assert speaker.voice == "custom"
    assert speaker.rate == 200


@patch('pyttsx3.init')
def test_speak(mock_init):
    """Test speak method."""
    mock_engine = Mock()
    mock_engine.getProperty.return_value = []  # Return empty list for voices
    mock_init.return_value = mock_engine
    
    speaker = AudioSpeaker()
    speaker.speak("Hallo Welt")
    
    mock_engine.say.assert_called_once_with("Hallo Welt")
    mock_engine.runAndWait.assert_called_once()


@patch('pyttsx3.init')
def test_get_available_voices(mock_init):
    """Test getting available voices."""
    mock_engine = Mock()
    mock_init.return_value = mock_engine
    
    # Mock voice objects
    mock_voice1 = Mock()
    mock_voice1.id = "voice1"
    mock_voice1.name = "German Voice"
    mock_voice1.languages = ["de_DE"]
    mock_voice1.gender = "male"
    
    mock_voice2 = Mock()
    mock_voice2.id = "voice2"
    mock_voice2.name = "English Voice"
    mock_voice2.languages = ["en_US"]
    mock_voice2.gender = "female"
    
    mock_engine.getProperty.return_value = [mock_voice1, mock_voice2]
    
    speaker = AudioSpeaker()
    voices = speaker.get_available_voices()
    
    assert len(voices) == 2
    assert voices[0]["id"] == "voice1"
    assert voices[0]["name"] == "German Voice"
    assert voices[0]["languages"] == ["de_DE"]
    assert voices[0]["gender"] == "male"


@patch('pyttsx3.init')
def test_set_rate(mock_init):
    """Test setting speech rate."""
    mock_engine = Mock()
    mock_engine.getProperty.return_value = []  # Return empty list for voices
    mock_init.return_value = mock_engine
    
    speaker = AudioSpeaker()
    speaker.set_rate(120)
    
    assert speaker.rate == 120
    mock_engine.setProperty.assert_called_with("rate", 120)


@patch('pyttsx3.init')
def test_configure_german_voice_found(mock_init):
    """Test German voice configuration when found."""
    mock_engine = Mock()
    mock_init.return_value = mock_engine
    
    # Mock German voice
    mock_german_voice = Mock()
    mock_german_voice.id = "german-voice"
    mock_german_voice.name = "German Voice"
    mock_german_voice.languages = ["de_DE"]
    
    mock_engine.getProperty.return_value = [mock_german_voice]
    
    AudioSpeaker()
    
    mock_engine.setProperty.assert_any_call("voice", "german-voice")
    mock_engine.setProperty.assert_any_call("rate", 150)


@patch('pyttsx3.init')
def test_configure_german_voice_fallback(mock_init):
    """Test German voice configuration fallback."""
    mock_engine = Mock()
    mock_init.return_value = mock_engine
    
    # Mock no German voices
    mock_english_voice = Mock()
    mock_english_voice.id = "english-voice"
    mock_english_voice.name = "English Voice"
    mock_english_voice.languages = ["en_US"]
    
    mock_engine.getProperty.return_value = [mock_english_voice]
    
    # Mock the fallback voice setting to raise ValueError (not found)
    mock_engine.setProperty.side_effect = [ValueError("Voice not found"), None]
    
    AudioSpeaker()
    
    # Should try to set German voice, then fallback to default
    assert mock_engine.setProperty.call_count >= 1
