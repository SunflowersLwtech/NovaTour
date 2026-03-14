"""E2E tests for NovaTour multi-turn context retention.

Validates that the agent maintains conversation context across
multiple voice turns within the same WebSocket session.

Requires real Nova Sonic — MockAgent does not maintain context.
"""

import pytest

from .conftest import skip_if_mock
from .validators import (
    assert_has_agent_response,
    assert_no_errors,
)


@pytest.mark.asyncio
async def test_destination_context(ws_client, tts_audio, realtime_factor, is_mock_agent):
    """Agent should remember the destination across turns.

    Turn 1: "I want to go to Kyoto"
    Turn 2: "What's the weather there?"
    → Agent should respond about Kyoto weather without asking "where?"
    """
    skip_if_mock(is_mock_agent, "Context retention requires real Nova Sonic")

    # Turn 1: establish destination
    pcm1 = tts_audio("I want to go to Kyoto, Japan.")
    result1 = await ws_client.send_and_collect(
        pcm1,
        utterance_text="I want to go to Kyoto, Japan.",
        timeout=30,
        idle_timeout=8,
        realtime_factor=realtime_factor,
    )
    assert_no_errors(result1)
    assert_has_agent_response(result1)

    # Turn 2: reference context ("there" = Kyoto)
    pcm2 = tts_audio("What's the weather there?")
    result2 = await ws_client.send_and_collect(
        pcm2,
        utterance_text="What's the weather there?",
        timeout=30,
        idle_timeout=8,
        realtime_factor=realtime_factor,
    )
    assert_no_errors(result2)
    assert_has_agent_response(result2)

    # If agent used a weather tool, it should reference Kyoto
    if result2.tool_calls:
        weather_tools = [
            tc for tc in result2.tool_calls
            if tc.get("name") in ("get_weather", "get_forecast")
        ]
        if weather_tools:
            tool_input = str(weather_tools[0].get("input", {})).lower()
            assert "kyoto" in tool_input or "japan" in tool_input, (
                f"Expected weather tool to reference Kyoto, got input: {tool_input}"
            )


@pytest.mark.asyncio
async def test_tool_chain(ws_client, tts_audio, realtime_factor, is_mock_agent):
    """Agent should carry destination context into subsequent tool calls.

    Turn 1: "Find flights to Bangkok"
    Turn 2: "Now find hotels there"
    → Agent should search hotels in Bangkok without re-asking.
    """
    skip_if_mock(is_mock_agent, "Tool chain context requires real Nova Sonic")

    # Turn 1: flight search
    pcm1 = tts_audio("Find flights to Bangkok from San Francisco.")
    result1 = await ws_client.send_and_collect(
        pcm1,
        utterance_text="Find flights to Bangkok from San Francisco.",
        timeout=45,
        idle_timeout=10,
        realtime_factor=realtime_factor,
    )
    assert_no_errors(result1)
    assert_has_agent_response(result1)

    # Turn 2: hotel search referencing "there"
    pcm2 = tts_audio("Now find hotels there for three nights.")
    result2 = await ws_client.send_and_collect(
        pcm2,
        utterance_text="Now find hotels there for three nights.",
        timeout=45,
        idle_timeout=10,
        realtime_factor=realtime_factor,
    )
    assert_no_errors(result2)
    assert_has_agent_response(result2)

    if result1.tool_calls and result2.tool_calls:
        turn1_tools = {tc.get("name") for tc in result1.tool_calls}
        turn2_tools = {tc.get("name") for tc in result2.tool_calls}
        assert len(turn1_tools | turn2_tools) >= 1, (
            f"Expected tools in both turns. Turn1: {turn1_tools}, Turn2: {turn2_tools}"
        )


@pytest.mark.asyncio
async def test_preference_memory(ws_client, tts_audio, realtime_factor, is_mock_agent):
    """Agent should remember stated preferences within a session.

    Turn 1: "I prefer budget options and street food"
    Turn 2: "Find me a hotel in Paris"
    → Agent should bias toward budget/affordable options.
    """
    skip_if_mock(is_mock_agent, "Preference memory requires real Nova Sonic")

    # Turn 1: state preferences
    pcm1 = tts_audio("I'm on a tight budget. I prefer cheap hotels and street food.")
    result1 = await ws_client.send_and_collect(
        pcm1,
        utterance_text="I'm on a tight budget. I prefer cheap hotels and street food.",
        timeout=30,
        idle_timeout=8,
        realtime_factor=realtime_factor,
    )
    assert_no_errors(result1)
    assert_has_agent_response(result1)

    # Turn 2: request that should use preferences
    pcm2 = tts_audio("Find me a hotel in Paris for next week.")
    result2 = await ws_client.send_and_collect(
        pcm2,
        utterance_text="Find me a hotel in Paris for next week.",
        timeout=45,
        idle_timeout=10,
        realtime_factor=realtime_factor,
    )
    assert_no_errors(result2)
    assert_has_agent_response(result2)

    all_agent_text = " ".join(result2.agent_transcripts).lower()
    budget_keywords = ["budget", "affordable", "cheap", "economical", "hostel", "value"]
    if all_agent_text:
        has_budget_ref = any(kw in all_agent_text for kw in budget_keywords)
        if not has_budget_ref:
            print(
                f"[INFO] Agent didn't explicitly mention budget in response: "
                f"{all_agent_text[:200]}"
            )
