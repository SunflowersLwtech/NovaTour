"""Parametrized structured conversation tests for NovaTour.

Runs declarative conversation scripts through the voice pipeline,
validating tool calls, keywords, and LOD changes at each turn.
"""

import pytest

from .conftest import skip_if_mock
from .conversations import ALL_CONVERSATIONS, Conversation, Turn
from .validators import (
    assert_agent_transcript_contains,
    assert_has_agent_response,
    assert_lod_changed,
    assert_no_errors,
    assert_tool_called,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "conversation",
    ALL_CONVERSATIONS,
    ids=lambda c: c.name,
)
async def test_structured_conversation(
    ws_client, tts_audio, realtime_factor, is_mock_agent, conversation: Conversation
):
    """Run a multi-turn conversation and validate each turn's expectations."""
    skip_if_mock(is_mock_agent, f"Conversation '{conversation.name}' requires real Nova Sonic")

    for i, turn in enumerate(conversation.turns):
        pcm = tts_audio(turn.utterance)
        result = await ws_client.send_and_collect(
            pcm,
            utterance_text=turn.utterance,
            timeout=turn.timeout,
            idle_timeout=8,
            realtime_factor=realtime_factor,
        )

        assert_no_errors(result)
        assert_has_agent_response(result), (
            f"Turn {i+1} ({turn.utterance[:30]}...) got no response"
        )

        # Validate expected tool calls
        for tool_name in turn.expect_tools:
            assert_tool_called(result, tool_name)

        # Validate expected keywords in agent response
        for keyword in turn.expect_keywords:
            assert_agent_transcript_contains(result, keyword)

        # Validate LOD changes
        if turn.expect_lod is not None:
            assert_lod_changed(result, turn.expect_lod)
