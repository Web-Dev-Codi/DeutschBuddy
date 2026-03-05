from __future__ import annotations

import json
import asyncio
from typing import AsyncGenerator

import ollama

from deutschbuddy.config import get_config


class OllamaClient:
    def __init__(self, host: str | None = None) -> None:
        config = get_config()
        self.host = host or config["ollama"]["host"]
        self.curriculum_model: str = config["ollama"]["curriculum_model"]
        self.interaction_model: str = config["ollama"]["interaction_model"]
        self._client = ollama.AsyncClient(host=self.host)

    async def chat(
        self,
        model: str,
        messages: list[dict],
        format: str | None = None,
    ) -> ollama.Message:
        response = await asyncio.wait_for(
            self._client.chat(
                model=model,
                messages=messages,
                format=format,
            ),
            timeout=30.0,
        )
        return response.message

    async def chat_json(self, model: str, messages: list[dict]) -> dict:
        """Send a chat request and return parsed JSON dict."""
        msg = await self.chat(model=model, messages=messages, format="json")
        return json.loads(msg.content)

    async def stream_chat(
        self, model: str, messages: list[dict]
    ) -> AsyncGenerator[str, None]:
        """Stream tokens for real-time TUI display."""
        async for chunk in self._client.chat(
            model=model, messages=messages, stream=True
        ):
            if chunk.message.content:
                yield chunk.message.content

    async def list_models(self) -> list[str]:
        """Return names of locally available Ollama models."""
        response = await self._client.list()
        return [m.model for m in response.models]
