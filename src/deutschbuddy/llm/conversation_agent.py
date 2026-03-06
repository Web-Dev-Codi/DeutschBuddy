"""Manages German conversation context with Ollama."""

from ollama import AsyncClient
from deutschbuddy.models.lesson import CEFRLevel


SYSTEM_PROMPTS = {
    "A1": """Du bist ein deutscher Sprachlehrer für Anfänger.
Antworte auf Deutsch, verwende sehr einfache Sätze.
Benutze grundlegenden Wortschatz und Präsens.
Korrigiere höflich Fehler am Ende deiner Antwort.""",

    "A2": """Du bist ein deutscher Sprachlehrer.
Antworte auf Deutsch, verwende einfache Sätze.
Benutze Perfekt und Modalverben.
Korrigiere höflich Fehler am Ende deiner Antwort.""",

    "B1": """Du bist ein deutscher Sprachlehrer für fortgeschrittene Lerner.
Antworte auf Deutsch mit natürlichem Tempo.
Verwende komplexe Sätze, Konjunktiv II und Passiv.
Korrigiere Fehler am Ende deiner Antwort.""",
}


class ConversationAgent:
    """Manages German conversation context with Ollama."""
    
    def __init__(
        self,
        ollama_client: AsyncClient,
        model: str = "mistral:7b-instruct",
        level: CEFRLevel = CEFRLevel.A1,
    ):
        """Initialize the conversation agent.
        
        Args:
            ollama_client: Ollama async client
            model: Model name for conversation
            level: CEFR proficiency level
        """
        self.client = ollama_client
        self.model = model
        self.level = level
        self.history: list[dict] = []
        self._system_prompt = SYSTEM_PROMPTS[level.value]
        
    async def chat(self, message: str) -> str:
        """Send message and receive AI response.
        
        Args:
            message: User's German text
            
        Returns:
            AI response in German
        """
        # Add user message to history
        self.history.append({"role": "user", "content": message})
        
        # Build messages with system prompt
        messages = [
            {"role": "system", "content": self._system_prompt},
            *self.history[-6:]  # Last 6 exchanges to maintain context
        ]
        
        # Query Ollama
        response = await self.client.chat(
            model=self.model,
            messages=messages,
        )
        
        ai_text = response["message"]["content"]
        
        # Add AI response to history
        self.history.append({"role": "assistant", "content": ai_text})
        
        return ai_text.strip()
        
    def set_level(self, level: CEFRLevel) -> None:
        """Adjust conversation difficulty level.
        
        Args:
            level: New CEFR level
        """
        self.level = level
        self._system_prompt = SYSTEM_PROMPTS[level.value]
        self.clear_history()
        
    def get_correction(self, user_text: str, ai_response: str) -> str:
        """Get grammar/vocabulary feedback on user input.
        
        Args:
            user_text: User's original text
            ai_response: AI's response
            
        Returns:
            Correction feedback in English/German
        """
        # This could be enhanced with a separate LLM call for corrections
        # For now, return a simple template
        return f"Original: {user_text}\nAI Response: {ai_response}"
        
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.history.clear()
