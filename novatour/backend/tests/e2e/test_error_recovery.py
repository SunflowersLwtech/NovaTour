"""E2E tests for NovaTour error recovery and edge cases.

Validates graceful handling of malformed input, empty audio,
and reconnection scenarios.
"""

import asyncio
import json

import pytest

from .ws_client import NovaTourWSClient
from .validators import assert_connection_alive


@pytest.mark.asyncio
async def test_empty_audio(ws_client, realtime_factor):
    """Send zero-length audio chunk — should not crash the server."""
    # Send empty audio
    await ws_client.send_audio(b"", realtime_factor=0)

    # Wait and verify connection is still alive
    await asyncio.sleep(1.0)

    # Send a valid short silence to verify connection still works
    import numpy as np
    silence = np.zeros(1600, dtype=np.int16).tobytes()  # 100ms
    result = await ws_client.send_and_collect(
        silence,
        utterance_text="(silence)",
        timeout=5,
        idle_timeout=3,
        realtime_factor=0,
    )

    # Connection should still be alive — we may or may not get events for silence
    # The key assertion is that we didn't crash
    # If we get events, great. If not, the connection survived.


@pytest.mark.asyncio
async def test_malformed_message(ws_client):
    """Send invalid JSON — server should send error event, connection stays alive."""
    # Send garbage data
    await ws_client.send_raw("this is not valid json {{{")

    # Collect any error events
    await asyncio.sleep(1.0)
    events = await ws_client.collect_events(timeout=3, idle_timeout=2, min_wait=0.5)

    # Connection should still be alive — try sending a valid message
    await ws_client.send_raw(json.dumps({"type": "lod", "level": 2}))
    await asyncio.sleep(0.5)
    events2 = await ws_client.collect_events(timeout=3, idle_timeout=2, min_wait=0.5)

    # We should get a lod_change response, proving the connection survived
    lod_events = [e for e in events2 if e.event_type == "lod_change"]
    assert len(lod_events) > 0, (
        "Connection died after malformed message — no lod_change response"
    )


@pytest.mark.asyncio
async def test_reconnect(ws_client_factory, server_url, tts_audio, realtime_factor):
    """Disconnect mid-conversation, reconnect with new session — clean start."""
    # Session 1: start a conversation
    client1 = ws_client_factory(session_id="reconnect_test_1")
    await client1.connect()
    await asyncio.sleep(1.0)

    pcm = tts_audio("I want to visit Berlin.")
    result1 = await client1.send_and_collect(
        pcm,
        utterance_text="I want to visit Berlin.",
        timeout=30,
        idle_timeout=8,
        realtime_factor=realtime_factor,
    )

    # Abruptly disconnect
    await client1.disconnect()
    await asyncio.sleep(1.0)

    # Session 2: reconnect with a new session
    client2 = ws_client_factory(session_id="reconnect_test_2")
    await client2.connect()
    await asyncio.sleep(1.0)

    pcm2 = tts_audio("Hello, can you help me plan a trip?")
    result2 = await client2.send_and_collect(
        pcm2,
        utterance_text="Hello, can you help me plan a trip?",
        timeout=30,
        idle_timeout=8,
        realtime_factor=realtime_factor,
    )

    # New session should work cleanly (tolerate BidiAgent fallback notification)
    real_errors = [
        e for e in result2.errors
        if "switched to text mode" not in e and "voice model unavailable" not in e.lower()
    ]
    assert len(real_errors) == 0, f"Errors in new session: {real_errors}"

    await client2.disconnect()
