"""E2E tests for NovaTour core voice pipeline.

Validates audio round-trip: TTS audio → WebSocket → Nova Sonic STT →
agent response (transcript + audio output).

With MockAgent: validates WebSocket connectivity and audio streaming protocol.
With BidiAgent: validates full STT, response generation, and audio output.
"""

import pytest

from .conftest import skip_if_mock
from .validators import (
    assert_audio_output_valid,
    assert_has_agent_response,
    assert_no_errors,
    assert_response_latency,
    assert_user_transcript_contains,
)


@pytest.mark.asyncio
async def test_greeting(ws_client, tts_audio, realtime_factor, is_mock_agent):
    """Send a greeting and verify agent responds with transcript + audio."""
    pcm = tts_audio("Hello, I'm planning a trip to Tokyo.")
    result = await ws_client.send_and_collect(
        pcm,
        utterance_text="Hello, I'm planning a trip to Tokyo.",
        timeout=30,
        idle_timeout=8,
        realtime_factor=realtime_factor,
    )

    assert_no_errors(result)
    assert_has_agent_response(result)

    if not is_mock_agent and result.user_transcripts:
        # Nova Sonic should transcribe "Tokyo" from the audio
        assert_user_transcript_contains(result, "tokyo")


@pytest.mark.asyncio
async def test_transcript_accuracy(ws_client, tts_audio, realtime_factor, is_mock_agent):
    """Send a clear question and verify STT transcription quality."""
    skip_if_mock(is_mock_agent, "STT transcription accuracy requires real Nova Sonic")

    text = "What is the best time to visit Paris in spring?"
    pcm = tts_audio(text)
    result = await ws_client.send_and_collect(
        pcm,
        utterance_text=text,
        timeout=30,
        idle_timeout=8,
        realtime_factor=realtime_factor,
    )

    assert_no_errors(result)
    assert_has_agent_response(result)
    if result.user_transcripts:
        assert_user_transcript_contains(result, "paris")
    if result.first_response_latency is not None:
        assert_response_latency(result, max_seconds=20.0)


@pytest.mark.asyncio
async def test_audio_output_format(ws_client, tts_audio, realtime_factor, is_mock_agent):
    """Verify server returns valid base64-encoded PCM audio chunks."""
    skip_if_mock(is_mock_agent, "Audio output requires real Nova Sonic")

    pcm = tts_audio("Tell me about Rome.")
    result = await ws_client.send_and_collect(
        pcm,
        utterance_text="Tell me about Rome.",
        timeout=30,
        idle_timeout=8,
        realtime_factor=realtime_factor,
    )

    assert_no_errors(result)
    if result.audio_chunks:
        assert_audio_output_valid(result, min_chunks=1)
