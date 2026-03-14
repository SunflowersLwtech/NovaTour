"""E2E tests for NovaTour barge-in and interruption handling.

Validates that the agent correctly handles user interruptions
during speech output.

Partially works with MockAgent (rapid turns test).
Full barge-in requires real Nova Sonic.
"""

import asyncio

import pytest

from .conftest import skip_if_mock
from .validators import assert_has_agent_response, assert_no_errors


@pytest.mark.asyncio
async def test_barge_in_during_speech(ws_client, tts_audio, realtime_factor, is_mock_agent):
    """Send new audio while agent is still responding — should trigger interruption.

    Strategy:
    1. Send a question that will produce a long response
    2. Wait briefly for agent to start responding
    3. Send another audio input (barge-in)
    4. Verify interruption event or new response
    """
    skip_if_mock(is_mock_agent, "Barge-in requires real Nova Sonic audio streaming")

    pcm1 = tts_audio("Tell me everything about visiting Japan, all the best cities and food.")
    await ws_client.send_audio(pcm1, realtime_factor=realtime_factor)

    # Wait for agent to start responding (but not finish)
    await asyncio.sleep(3.0)

    # Barge in
    pcm2 = tts_audio("Actually, tell me about Thailand instead.")
    result = await ws_client.send_and_collect(
        pcm2,
        utterance_text="Actually, tell me about Thailand instead.",
        timeout=30,
        idle_timeout=8,
        realtime_factor=realtime_factor,
    )

    assert_has_agent_response(result)
    assert_no_errors(result)


@pytest.mark.asyncio
async def test_rapid_turns(ws_client, tts_audio, realtime_factor):
    """Send 3 utterances in quick succession — system should not crash.

    Works with both MockAgent and BidiAgent.
    """
    utterances = [
        "What time is it in Tokyo?",
        "How about in London?",
        "And what about New York?",
    ]

    last_result = None
    for text in utterances:
        pcm = tts_audio(text)
        result = await ws_client.send_and_collect(
            pcm,
            utterance_text=text,
            timeout=20,
            idle_timeout=5,
            realtime_factor=realtime_factor * 2,
        )
        last_result = result
        assert_no_errors(result)

    if last_result:
        assert_has_agent_response(last_result)
