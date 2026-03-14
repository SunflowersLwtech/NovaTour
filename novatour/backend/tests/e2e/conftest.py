"""Shared fixtures for NovaTour E2E tests.

Provides:
- GeminiTTS instance (session-scoped, cached)
- WebSocket client factory
- tts_audio helper for generating test audio
- Server URL configuration via --server-url pytest arg
- Agent mode detection (BidiAgent vs MockAgent)
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from typing import AsyncGenerator, Callable

import pytest
import pytest_asyncio
import websockets

from .gemini_tts import GeminiTTS, generate_silence
from .ws_client import NovaTourWSClient

# ── pytest CLI options ──────────────────────────────────────


def pytest_addoption(parser):
    parser.addoption(
        "--server-url",
        default=os.getenv("NOVATOUR_SERVER_URL", "ws://localhost:8000"),
        help="NovaTour WebSocket server URL (default: ws://localhost:8000)",
    )
    parser.addoption(
        "--gemini-key",
        default=os.getenv("GEMINI_API_KEY", ""),
        help="Gemini API key for TTS generation",
    )
    parser.addoption(
        "--realtime-factor",
        default=float(os.getenv("NOVATOUR_REALTIME_FACTOR", "1.5")),
        type=float,
        help="Audio streaming speed factor (1.0=realtime, higher=faster)",
    )


# ── Session-scoped fixtures ─────────────────────────────────


@pytest.fixture(scope="session")
def server_url(request) -> str:
    return request.config.getoption("--server-url")


@pytest.fixture(scope="session")
def gemini_key(request) -> str:
    return request.config.getoption("--gemini-key")


@pytest.fixture(scope="session")
def realtime_factor(request) -> float:
    return request.config.getoption("--realtime-factor")


@pytest.fixture(scope="session")
def tts(gemini_key) -> GeminiTTS:
    """Session-scoped Gemini TTS client with caching."""
    return GeminiTTS(api_key=gemini_key)


@pytest.fixture(scope="session")
def is_mock_agent(server_url) -> bool:
    """Detect whether the server is using MockAgent (directly or via fallback).

    Sends a probe audio chunk and checks if:
    1. An immediate greeting arrives (MockAgent auto-greets)
    2. An error + fallback greeting arrives (BidiAgent failed, fell back)
    3. No immediate response (real BidiAgent is working)
    """
    async def _detect():
        url = f"{server_url}/ws/voice/agent_detect_probe"
        try:
            async with websockets.connect(url) as ws:
                # Send a small silence chunk to trigger BidiAgent
                silence = b"\x00" * 2560
                b64 = base64.b64encode(silence).decode()
                await ws.send(json.dumps({"type": "audio", "data": b64}))

                # Collect events for up to 12 seconds
                events = []
                for _ in range(20):
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=3)
                        data = json.loads(msg)
                        events.append(data)
                        etype = data.get("type", "")
                        text = data.get("text", "").lower()

                        # MockAgent greeting or fallback error
                        if etype == "error" and "unavailable" in data.get("message", "").lower():
                            return True
                        if etype == "transcript" and (
                            "unavailable" in text
                            or "mock" in text
                            or "text mode" in text
                        ):
                            return True

                        # BidiAgent responding with real audio/transcript
                        if etype == "audio":
                            return False
                        if etype == "transcript" and "unavailable" not in text:
                            return False
                    except asyncio.TimeoutError:
                        break

                # No definitive signal — if we got error events, it's mock
                for e in events:
                    if e.get("type") == "error":
                        return True
                # No response at all after audio → likely BidiAgent processing
                return len(events) == 0

        except Exception:
            return True  # Can't connect → assume mock

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_detect())
    finally:
        loop.close()


# ── Function-scoped fixtures ────────────────────────────────


@pytest_asyncio.fixture
async def ws_client(server_url) -> AsyncGenerator[NovaTourWSClient, None]:
    """Create a connected WebSocket client, cleaned up after test."""
    client = NovaTourWSClient(server_url)
    await client.connect()
    # Wait for server to initialize the agent (including possible fallback)
    await asyncio.sleep(2.0)
    yield client
    await client.disconnect()


@pytest.fixture
def ws_client_factory(server_url) -> Callable[..., NovaTourWSClient]:
    """Factory for creating multiple WebSocket clients (e.g., reconnect tests)."""
    clients: list[NovaTourWSClient] = []

    def _create(session_id: str | None = None) -> NovaTourWSClient:
        client = NovaTourWSClient(server_url, session_id=session_id)
        clients.append(client)
        return client

    return _create


@pytest.fixture
def tts_audio(tts) -> Callable[[str], bytes]:
    """Generate TTS audio for a given text. Returns 16kHz mono PCM bytes."""
    def _generate(text: str) -> bytes:
        return tts.synthesize(text)
    return _generate


@pytest.fixture
def silence() -> Callable[[int], bytes]:
    """Generate silent PCM audio of given duration in ms."""
    return generate_silence


def skip_if_mock(is_mock_agent: bool, reason: str = "Requires real Nova Sonic"):
    """Helper to skip tests when MockAgent is active."""
    if is_mock_agent:
        pytest.skip(reason)
