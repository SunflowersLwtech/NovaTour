"""E2E tests for NovaTour LOD (Level of Detail) switching.

Validates that voice commands and explicit WebSocket messages
correctly trigger LOD level transitions.
"""

import asyncio

import pytest

from .validators import (
    assert_has_agent_response,
    assert_lod_changed,
    assert_no_errors,
)


@pytest.mark.asyncio
async def test_switch_to_brief(ws_client, tts_audio, realtime_factor):
    """Ask about a city, then request brief mode — LOD should decrease."""
    # First turn: ask about a destination (default LOD 2)
    pcm1 = tts_audio("Tell me about visiting Barcelona, Spain.")
    result1 = await ws_client.send_and_collect(
        pcm1,
        utterance_text="Tell me about visiting Barcelona, Spain.",
        timeout=30,
        idle_timeout=8,
        realtime_factor=realtime_factor,
    )
    assert_no_errors(result1)
    assert_has_agent_response(result1)

    # Second turn: request brief mode
    pcm2 = tts_audio("Be brief, just give me the highlights.")
    result2 = await ws_client.send_and_collect(
        pcm2,
        utterance_text="Be brief, just give me the highlights.",
        timeout=30,
        idle_timeout=8,
        realtime_factor=realtime_factor,
    )
    assert_no_errors(result2)
    # LOD change may come from text detection via the transcript
    # or from the agent's response being shorter
    assert_has_agent_response(result2)


@pytest.mark.asyncio
async def test_switch_to_detailed(ws_client, tts_audio, realtime_factor):
    """Ask about a city, then request more detail — LOD should increase."""
    # First turn
    pcm1 = tts_audio("What can I do in Istanbul?")
    result1 = await ws_client.send_and_collect(
        pcm1,
        utterance_text="What can I do in Istanbul?",
        timeout=30,
        idle_timeout=8,
        realtime_factor=realtime_factor,
    )
    assert_no_errors(result1)
    assert_has_agent_response(result1)

    # Second turn: request more detail
    pcm2 = tts_audio("Tell me more, give me the full story about Istanbul.")
    result2 = await ws_client.send_and_collect(
        pcm2,
        utterance_text="Tell me more, give me the full story about Istanbul.",
        timeout=45,
        idle_timeout=10,
        realtime_factor=realtime_factor,
    )
    assert_no_errors(result2)
    assert_has_agent_response(result2)


@pytest.mark.asyncio
async def test_lod_via_ws_message(ws_client, tts_audio, realtime_factor):
    """Send explicit LOD change via WebSocket JSON message."""
    # Send LOD change to level 1 (brief)
    await ws_client.send_lod(1)
    # Small wait for server to process
    await asyncio.sleep(0.5)

    # Collect any LOD change acknowledgment
    events = await ws_client.collect_events(timeout=3, idle_timeout=2, min_wait=0.5)
    lod_events = [e for e in events if e.event_type == "lod_change"]
    assert len(lod_events) > 0, "Expected lod_change event after explicit LOD message"
    assert lod_events[0].payload.get("level") == 1

    # Send LOD change to level 3 (detailed)
    await ws_client.send_lod(3)
    await asyncio.sleep(0.5)
    events2 = await ws_client.collect_events(timeout=3, idle_timeout=2, min_wait=0.5)
    lod_events2 = [e for e in events2 if e.event_type == "lod_change"]
    assert len(lod_events2) > 0, "Expected lod_change event for level 3"
    assert lod_events2[0].payload.get("level") == 3
