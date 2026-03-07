"""Manages German conversation context with Ollama."""

from __future__ import annotations

from typing import Any

from deutschbuddy.config import get_config
from deutschbuddy.llm.client import OllamaClient


DEFAULT_SYSTEM_PROMPT = """Du bist ein freundlicher Gesprächspartner für freie Gespräche auf Deutsch.
Antworte immer auf natürlichem Deutsch.
Bleibe gesprächig, freundlich und locker.
Gib keine Korrekturen, keine Bewertungen, keine Lektionserklärungen und kein Coaching,
außer die Nutzerin oder der Nutzer bittet ausdrücklich darum.
Wenn es gut passt, stelle genau eine kurze Anschlussfrage, damit das Gespräch weitergeht."""

DEFAULT_GREETING = "Hallo! Wir können jetzt frei auf Deutsch sprechen. Womit möchtest du anfangen?"


class ConversationAgent:
    def __init__(
        self,
        ollama_client: OllamaClient,
        model: str | None = None,
        system_prompt: str | None = None,
        greeting: str | None = None,
    ) -> None:
        config = get_config().get("conversation", {})
        self.client = ollama_client
        self.model = model or config.get("model") or ollama_client.interaction_model
        self.history: list[dict[str, Any]] = []
        self._system_prompt = system_prompt or config.get("system_prompt") or DEFAULT_SYSTEM_PROMPT
        self._greeting = greeting or config.get("greeting") or DEFAULT_GREETING

    def start_session(self) -> str:
        self.clear_history()
        return self._greeting

    async def chat(self, message: str) -> str:
        cleaned_message = message.strip()
        if not cleaned_message:
            return ""

        self.history.append({"role": "user", "content": cleaned_message})
        messages = [
            {"role": "system", "content": self._system_prompt},
            *self.history[-10:],
        ]
        response = await self.client.chat(model=self.model, messages=messages)
        ai_text = response.content.strip()
        if ai_text:
            self.history.append({"role": "assistant", "content": ai_text})
        return ai_text

    def clear_history(self) -> None:
        self.history.clear()
