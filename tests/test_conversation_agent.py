"""Tests for ConversationAgent class."""

from unittest.mock import AsyncMock, Mock, patch
from deutschbuddy.llm.conversation_agent import ConversationAgent
from deutschbuddy.models.lesson import CEFRLevel


@patch('deutschbuddy.llm.conversation_agent.AsyncClient')
def test_agent_init(mock_client_class):
    """Test ConversationAgent initialization."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    agent = ConversationAgent(mock_client)
    
    assert agent.model == "mistral:7b-instruct"
    assert agent.level == CEFRLevel.A1
    assert agent.history == []
    assert "Du bist ein deutscher Sprachlehrer für Anfänger" in agent._system_prompt


@patch('deutschbuddy.llm.conversation_agent.AsyncClient')
def test_agent_init_custom_level(mock_client_class):
    """Test ConversationAgent initialization with custom level."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    agent = ConversationAgent(mock_client, level=CEFRLevel.B1)
    
    assert agent.level == CEFRLevel.B1
    assert "fortgeschrittene Lerner" in agent._system_prompt


@patch('deutschbuddy.llm.conversation_agent.AsyncClient')
async def test_chat_response(mock_client_class):
    """Test chat response generation."""
    mock_client = AsyncMock()
    mock_client_class.return_value = mock_client
    
    # Mock Ollama response
    mock_response = {
        "message": {
            "content": "Hallo! Wie geht es Ihnen?"
        }
    }
    mock_client.chat.return_value = mock_response
    
    agent = ConversationAgent(mock_client, level=CEFRLevel.A1)
    response = await agent.chat("Guten Tag!")
    
    assert response == "Hallo! Wie geht es Ihnen?"
    assert len(agent.history) == 2
    assert agent.history[0]["role"] == "user"
    assert agent.history[0]["content"] == "Guten Tag!"
    assert agent.history[1]["role"] == "assistant"
    assert agent.history[1]["content"] == "Hallo! Wie geht es Ihnen?"


@patch('deutschbuddy.llm.conversation_agent.AsyncClient')
async def test_chat_with_history(mock_client_class):
    """Test chat with conversation history."""
    mock_client = AsyncMock()
    mock_client_class.return_value = mock_client
    
    # Add some history
    mock_response = {"message": {"content": "Sehr gut!"}}
    mock_client.chat.return_value = mock_response
    
    agent = ConversationAgent(mock_client, level=CEFRLevel.A1)
    agent.history = [
        {"role": "user", "content": "Wie geht es Ihnen?"},
        {"role": "assistant", "content": "Mir geht es gut!"}
    ]
    
    await agent.chat("Und Ihnen?")
    
    # Check that system prompt and history were sent
    call_args = mock_client.chat.call_args
    messages = call_args[1]["messages"]
    
    assert len(messages) >= 3  # system + existing history + new message
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == agent._system_prompt


@patch('deutschbuddy.llm.conversation_agent.AsyncClient')
def test_level_change(mock_client_class):
    """Test changing CEFR level."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    agent = ConversationAgent(mock_client, level=CEFRLevel.A1)
    agent.history = [{"role": "user", "content": "test"}]
    
    agent.set_level(CEFRLevel.B1)
    
    assert agent.level == CEFRLevel.B1
    assert "fortgeschrittene Lerner" in agent._system_prompt
    assert agent.history == []  # History should be cleared


@patch('deutschbuddy.llm.conversation_agent.AsyncClient')
def test_clear_history(mock_client_class):
    """Test clearing conversation history."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    agent = ConversationAgent(mock_client)
    agent.history = [
        {"role": "user", "content": "message1"},
        {"role": "assistant", "content": "response1"}
    ]
    
    agent.clear_history()
    
    assert agent.history == []


@patch('deutschbuddy.llm.conversation_agent.AsyncClient')
def test_get_correction(mock_client_class):
    """Test getting correction feedback."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    agent = ConversationAgent(mock_client)
    
    user_text = "Ich bin ein student"
    ai_response = "Ich bin ein Student."
    
    correction = agent.get_correction(user_text, ai_response)
    
    assert user_text in correction
    assert ai_response in correction
