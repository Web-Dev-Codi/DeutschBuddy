from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Literal

from deutschbuddy.audio.listener import AudioListener
from deutschbuddy.audio.speaker import AudioSpeaker
from deutschbuddy.config import get_config
from deutschbuddy.llm.conversation_agent import ConversationAgent


SpeakerRole = Literal["user", "assistant"]


@dataclass(slots=True)
class ConversationTurn:
    role: SpeakerRole
    text: str


class VoiceConversationSession:
    def __init__(
        self,
        listener: AudioListener,
        speaker: AudioSpeaker,
        agent: ConversationAgent,
    ) -> None:
        config = get_config().get("conversation", {})
        self.listener = listener
        self.speaker = speaker
        self.agent = agent
        self.listen_timeout = int(config.get("listen_timeout", 5))
        self.calibration_duration = float(config.get("calibration_duration", 1.0))
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    async def start(self) -> str:
        self._active = True
        await asyncio.to_thread(
            self.listener.calibrate,
            self.calibration_duration,
        )
        if not self._active:
            return ""
        return self.agent.start_session()

    def stop(self) -> None:
        self._active = False
        self.speaker.stop()

    async def listen(self) -> str:
        if not self._active:
            return ""
        return await asyncio.to_thread(
            self.listener.listen,
            self.listen_timeout,
        )

    async def respond(self, text: str) -> str:
        if not self._active:
            return ""
        return await self.agent.chat(text)

    async def speak(self, text: str) -> None:
        if not self._active or not text.strip():
            return
        await asyncio.to_thread(self.speaker.speak, text)
