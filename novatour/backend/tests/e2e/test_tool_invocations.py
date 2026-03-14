"""E2E tests for NovaTour travel tool invocations.

Validates that voice requests trigger the correct travel tools
(flights, hotels, weather, places, itinerary) and return results.

Requires real Nova Sonic — MockAgent does not invoke tools.
"""

import pytest

from .conftest import skip_if_mock
from .validators import (
    assert_has_agent_response,
    assert_itinerary_received,
    assert_no_errors,
    assert_tool_called,
    assert_tool_completed,
)


@pytest.mark.asyncio
async def test_flight_search(ws_client, tts_audio, realtime_factor, is_mock_agent):
    """Voice request for flights should trigger search_flights tool."""
    skip_if_mock(is_mock_agent, "Tool invocation requires real Nova Sonic")

    pcm = tts_audio("Find me flights from New York to London on April 15th.")
    result = await ws_client.send_and_collect(
        pcm,
        utterance_text="Find me flights from New York to London on April 15th.",
        timeout=45,
        idle_timeout=10,
        realtime_factor=realtime_factor,
    )

    assert_no_errors(result)
    assert_has_agent_response(result)
    if result.tool_calls:
        tc = assert_tool_called(result, "search_flights")
        statuses = [t.get("status") for t in result.tool_calls if t.get("name") == "search_flights"]
        assert "complete" in statuses or "calling" in statuses


@pytest.mark.asyncio
async def test_hotel_search(ws_client, tts_audio, realtime_factor, is_mock_agent):
    """Voice request for hotels should trigger search_hotels tool."""
    skip_if_mock(is_mock_agent, "Tool invocation requires real Nova Sonic")

    pcm = tts_audio("Search for hotels in Tokyo for April 20th to April 25th.")
    result = await ws_client.send_and_collect(
        pcm,
        utterance_text="Search for hotels in Tokyo for April 20th to April 25th.",
        timeout=45,
        idle_timeout=10,
        realtime_factor=realtime_factor,
    )

    assert_no_errors(result)
    assert_has_agent_response(result)
    if result.tool_calls:
        assert_tool_called(result, "search_hotels")


@pytest.mark.asyncio
async def test_weather(ws_client, tts_audio, realtime_factor, is_mock_agent):
    """Voice request for weather should trigger get_weather tool."""
    skip_if_mock(is_mock_agent, "Tool invocation requires real Nova Sonic")

    pcm = tts_audio("What's the weather like in Bangkok right now?")
    result = await ws_client.send_and_collect(
        pcm,
        utterance_text="What's the weather like in Bangkok right now?",
        timeout=45,
        idle_timeout=10,
        realtime_factor=realtime_factor,
    )

    assert_no_errors(result)
    assert_has_agent_response(result)
    if result.tool_calls:
        weather_tools = [
            tc for tc in result.tool_calls
            if tc.get("name") in ("get_weather", "get_forecast")
        ]
        assert len(weather_tools) > 0, (
            f"Expected weather tool call, got: "
            f"{[tc.get('name') for tc in result.tool_calls]}"
        )


@pytest.mark.asyncio
async def test_places(ws_client, tts_audio, realtime_factor, is_mock_agent):
    """Voice request for nearby places should trigger search_places tool."""
    skip_if_mock(is_mock_agent, "Tool invocation requires real Nova Sonic")

    pcm = tts_audio("Find good restaurants near the Eiffel Tower.")
    result = await ws_client.send_and_collect(
        pcm,
        utterance_text="Find good restaurants near the Eiffel Tower.",
        timeout=45,
        idle_timeout=10,
        realtime_factor=realtime_factor,
    )

    assert_no_errors(result)
    assert_has_agent_response(result)
    if result.tool_calls:
        assert_tool_called(result, "search_places")


@pytest.mark.asyncio
async def test_itinerary(ws_client, tts_audio, realtime_factor, is_mock_agent):
    """Voice request for trip planning should trigger plan_itinerary tool."""
    skip_if_mock(is_mock_agent, "Tool invocation requires real Nova Sonic")

    pcm = tts_audio("Plan a 3-day itinerary for Seoul, South Korea.")
    result = await ws_client.send_and_collect(
        pcm,
        utterance_text="Plan a 3-day itinerary for Seoul, South Korea.",
        timeout=60,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )

    assert_no_errors(result)
    assert_has_agent_response(result)
    if result.tool_calls:
        assert_tool_called(result, "plan_itinerary")
    if result.itineraries:
        assert_itinerary_received(result)
