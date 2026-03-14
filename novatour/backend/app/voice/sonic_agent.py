"""BidiAgent creation for Nova Sonic voice pipeline.

Creates a BidiAgent instance with dual-path fallback:
1. Primary: Strands BidiAgent with Nova Sonic
2. Fallback: Mock agent for development/testing
"""

import asyncio
import logging

from app.config import settings
from app.lod.prompt_builder import build_system_prompt
from app.tools import ALL_TOOLS

logger = logging.getLogger(__name__)


def create_voice_agent(session_id: str, lod_level: int = 2):
    """Create a BidiAgent for voice conversation.

    Args:
        session_id: Unique session identifier
        lod_level: LOD level for system prompt (1, 2, or 3)

    Returns:
        BidiAgent instance or MockAgent if BidiAgent unavailable
    """
    system_prompt = build_system_prompt(lod_level=lod_level)

    try:
        from strands.experimental.bidi.agent.agent import BidiAgent
        from strands.experimental.bidi.models.nova_sonic import (
            NOVA_SONIC_V1_MODEL_ID,
            BidiNovaSonicModel,
        )

        model_id = settings.nova_sonic_model_id
        is_v1 = model_id == NOVA_SONIC_V1_MODEL_ID

        provider_config = {
            "audio": {
                "voice": "matthew",
                "input_rate": 16000,
                "output_rate": 24000,
                "channels": 1,
                "format": "pcm",
            },
            "inference": {"temperature": 0.7, "max_tokens": 1024, "top_p": 0.95},
        }
        # turn_detection is v2-only
        if not is_v1:
            provider_config["turn_detection"] = {"endpointingSensitivity": "MEDIUM"}

        if is_v1:
            logger.info("Using Nova Sonic v1 (turn_detection disabled)")

        model = BidiNovaSonicModel(
            model_id=model_id,
            client_config={"region": settings.aws_default_region},
            provider_config=provider_config,
        )

        agent = BidiAgent(
            model=model,
            tools=ALL_TOOLS,
            system_prompt=system_prompt,
            agent_id=session_id,
            name="NovaTour",
            description="AI voice travel assistant",
        )
        logger.info(f"Created BidiAgent for session {session_id}")
        return agent

    except Exception as e:
        logger.warning(f"BidiAgent creation failed: {e}, using MockAgent")
        return MockAgent(session_id=session_id, system_prompt=system_prompt)


class MockAgent:
    """Fallback agent for development when Nova Sonic is unavailable.

    Mimics BidiAgent interface. Queues responses when send() is called
    and yields them from receive().
    """

    def __init__(self, session_id: str, system_prompt: str):
        self.session_id = session_id
        self.system_prompt = system_prompt
        self._running = False
        self._queue: asyncio.Queue = asyncio.Queue()

    async def start(self):
        self._running = True
        # Send initial greeting
        self._queue.put_nowait(
            MockTranscriptEvent(
                text="I'm NovaTour, your AI travel assistant. "
                "Nova Sonic is currently unavailable, but I'm here in text mode. "
                "How can I help you plan your trip?",
                role="assistant",
                is_final=True,
            )
        )

    async def stop(self):
        self._running = False
        # Unblock receive() if waiting
        self._queue.put_nowait(None)

    async def send(self, data):
        """Queue a mock response for any input."""
        text = data if isinstance(data, str) else "I received your audio input."
        self._queue.put_nowait(
            MockTranscriptEvent(
                text=f"[Mock] I heard: '{text[:100]}'. "
                "In production, Nova Sonic would process this with voice AI.",
                role="assistant",
                is_final=True,
            )
        )

    async def receive(self):
        """Yield events from the queue until stopped."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=30.0)
                if event is None:
                    break
                yield event
            except asyncio.TimeoutError:
                continue


class MockTranscriptEvent:
    """Mock event for development."""

    def __init__(self, text: str, role: str = "assistant", is_final: bool = True):
        self.text = text
        self.role = role
        self.is_final = is_final
