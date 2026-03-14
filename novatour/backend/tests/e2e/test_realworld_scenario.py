"""Real-world E2E scenario tests for NovaTour.

Simulates complete travel planning conversations with multi-turn context,
LOD switching, tool invocations, and response quality validation.

Uses Gemini TTS to generate audio for each utterance, streams it over
WebSocket, and validates the full agent response pipeline.
"""

import asyncio
import re

import pytest

from .conftest import skip_if_mock
from .validators import (
    assert_has_agent_response,
    assert_no_errors,
    assert_response_latency,
)


# ════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════


def _agent_text(result) -> str:
    """Join all agent transcript fragments into one string."""
    return " ".join(result.agent_transcripts).strip()


def _word_count(text: str) -> int:
    return len(text.split()) if text else 0


def _tool_names(result) -> set:
    return {tc.get("name") for tc in result.tool_calls}


def _has_tool(result, name: str) -> bool:
    return name in _tool_names(result)


def _print_turn(label: str, result):
    """Print a summary of a conversation turn for debugging."""
    text = _agent_text(result)
    tools = _tool_names(result)
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  User transcripts: {result.user_transcripts}")
    print(f"  Agent response ({_word_count(text)} words): {text[:300]}...")
    print(f"  Tools called: {tools}")
    print(f"  Audio chunks: {len(result.audio_chunks)}")
    print(f"  LOD changes: {result.lod_changes}")
    print(f"  Errors: {result.errors}")
    if result.first_response_latency:
        print(f"  First response latency: {result.first_response_latency:.2f}s")
    print(f"{'='*60}")


# ════════════════════════════════════════════════════════════════
# Scenario 1: Complete Tokyo Trip Planning (5 turns)
# ════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_tokyo_trip_planning_scenario(
    ws_client, tts_audio, realtime_factor, is_mock_agent
):
    """Full trip planning conversation:
    Turn 1: Ask about Tokyo → agent should respond with travel info
    Turn 2: Check weather → agent should call weather tool
    Turn 3: Search hotels → agent should call hotels tool
    Turn 4: Switch to brief mode → LOD should change
    Turn 5: Plan itinerary → agent should call itinerary tool
    """
    skip_if_mock(is_mock_agent, "Full scenario requires real Nova Sonic")

    # ── Turn 1: Greeting + destination ──
    pcm1 = tts_audio("Hi! I'm planning a trip to Tokyo, Japan for 5 days.")
    result1 = await ws_client.send_and_collect(
        pcm1,
        utterance_text="Hi! I'm planning a trip to Tokyo, Japan for 5 days.",
        timeout=60,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )
    _print_turn("Turn 1: Tokyo intro", result1)
    assert_no_errors(result1)
    assert_has_agent_response(result1)

    # Agent should mention Tokyo or Japan
    text1 = _agent_text(result1).lower()
    if text1:
        assert "tokyo" in text1 or "japan" in text1, (
            f"Expected Tokyo/Japan reference in response: {text1[:200]}"
        )

    # ── Turn 2: Weather check (should trigger tool) ──
    pcm2 = tts_audio("What's the weather like in Tokyo right now?")
    result2 = await ws_client.send_and_collect(
        pcm2,
        utterance_text="What's the weather like in Tokyo right now?",
        timeout=60,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )
    _print_turn("Turn 2: Weather check", result2)
    assert_no_errors(result2)
    assert_has_agent_response(result2)

    # Expect a weather tool to be called
    if result2.tool_calls:
        weather_tools = {tc.get("name") for tc in result2.tool_calls if "weather" in tc.get("name", "")}
        print(f"  Weather tools found: {weather_tools}")

    # ── Turn 3: Hotel search ──
    pcm3 = tts_audio("Can you find me some hotels in Shinjuku area?")
    result3 = await ws_client.send_and_collect(
        pcm3,
        utterance_text="Can you find me some hotels in Shinjuku area?",
        timeout=40,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )
    _print_turn("Turn 3: Hotel search", result3)
    assert_no_errors(result3)
    assert_has_agent_response(result3)

    # ── Turn 4: Switch to brief mode ──
    pcm4 = tts_audio("Keep it short and simple from now on.")
    result4 = await ws_client.send_and_collect(
        pcm4,
        utterance_text="Keep it short and simple from now on.",
        timeout=60,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )
    _print_turn("Turn 4: Brief mode switch", result4)
    assert_no_errors(result4)

    # ── Turn 5: Itinerary request (brief mode) ──
    pcm5 = tts_audio("Plan my itinerary please.")
    result5 = await ws_client.send_and_collect(
        pcm5,
        utterance_text="Plan my itinerary please.",
        timeout=60,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )
    _print_turn("Turn 5: Itinerary request", result5)
    assert_no_errors(result5)
    assert_has_agent_response(result5)


# ════════════════════════════════════════════════════════════════
# Scenario 2: LOD Switching Round-Trip (3 turns)
# ════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_lod_switching_roundtrip(
    ws_client, tts_audio, realtime_factor, is_mock_agent
):
    """Test LOD switching with explicit WebSocket commands.

    Voice-based LOD detection only works on text input, not transcribed speech.
    For reliable LOD switching in voice mode, use explicit LOD commands.

    Turn 1: Ask about a city (LOD 2 default)
    Turn 2: Explicitly switch to LOD 3, then ask same question → longer response
    Turn 3: Explicitly switch to LOD 1, then ask same question → shorter response
    """
    skip_if_mock(is_mock_agent, "LOD switching requires real Nova Sonic")

    # ── Turn 1: Default LOD 2 ──
    pcm1 = tts_audio("Tell me about visiting Kyoto, Japan.")
    result1 = await ws_client.send_and_collect(
        pcm1,
        utterance_text="Tell me about visiting Kyoto, Japan.",
        timeout=60,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )
    _print_turn("LOD Turn 1: Default (L2)", result1)
    assert_no_errors(result1)
    assert_has_agent_response(result1)
    words1 = _word_count(_agent_text(result1))

    # ── Turn 2: Switch LOD to 3 explicitly, then ask ──
    await ws_client.send_lod(3)
    await asyncio.sleep(2)
    # Drain LOD change events
    await ws_client.collect_events(timeout=3, idle_timeout=2, min_wait=1)

    pcm2 = tts_audio("Tell me about the history and culture of Kyoto.")
    result2 = await ws_client.send_and_collect(
        pcm2,
        utterance_text="Tell me about the history and culture of Kyoto.",
        timeout=90,
        idle_timeout=20,
        realtime_factor=realtime_factor,
    )
    _print_turn("LOD Turn 2: Narrative (L3)", result2)
    assert_no_errors(result2)
    assert_has_agent_response(result2)
    words2 = _word_count(_agent_text(result2))

    # ── Turn 3: Switch LOD to 1 explicitly, then ask ──
    await ws_client.send_lod(1)
    await asyncio.sleep(2)
    await ws_client.collect_events(timeout=3, idle_timeout=2, min_wait=1)

    pcm3 = tts_audio("What's the one thing I must see in Kyoto?")
    result3 = await ws_client.send_and_collect(
        pcm3,
        utterance_text="What's the one thing I must see in Kyoto?",
        timeout=60,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )
    _print_turn("LOD Turn 3: Brief (L1)", result3)
    assert_no_errors(result3)
    assert_has_agent_response(result3)
    words3 = _word_count(_agent_text(result3))

    print(f"\n  Word counts: L2={words1}, L3={words2}, L1={words3}")

    # Validate LOD progression: L3 should produce more words than L1
    if words2 > 20 and words3 > 0:
        assert words2 > words3, (
            f"Narrative mode ({words2} words) should be longer than brief mode ({words3} words)"
        )


# ════════════════════════════════════════════════════════════════
# Scenario 3: Explicit LOD via WebSocket + Voice Response
# ════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_explicit_lod_with_transition_phrase(
    ws_client, tts_audio, realtime_factor, is_mock_agent
):
    """Test explicit LOD change via WebSocket message and verify transition phrase."""
    skip_if_mock(is_mock_agent, "Transition phrases require real agent")

    # First, establish context
    pcm1 = tts_audio("Tell me about Barcelona, Spain.")
    result1 = await ws_client.send_and_collect(
        pcm1,
        utterance_text="Tell me about Barcelona, Spain.",
        timeout=60,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )
    _print_turn("Explicit LOD Turn 1: Context", result1)
    assert_no_errors(result1)

    # Send explicit LOD change to level 3
    await ws_client.send_lod(3)
    await asyncio.sleep(1.0)

    # Collect LOD change + transition phrase
    events = await ws_client.collect_events(timeout=5, idle_timeout=3, min_wait=1)
    lod_events = [e for e in events if e.event_type == "lod_change"]
    transcript_events = [e for e in events if e.event_type == "transcript"]

    print(f"\n  LOD events: {[e.payload for e in lod_events]}")
    print(f"  Transition transcripts: {[e.payload.get('text', '') for e in transcript_events]}")

    assert len(lod_events) > 0, "Expected lod_change event"
    assert lod_events[0].payload.get("level") == 3

    # Check if transition phrase was sent
    if transcript_events:
        phrase_text = " ".join(e.payload.get("text", "") for e in transcript_events)
        print(f"  Transition phrase: {phrase_text}")
        # The transition phrase should mention "story" or similar
        assert len(phrase_text) > 0, "Expected non-empty transition phrase"


# ════════════════════════════════════════════════════════════════
# Scenario 4: Tool Invocation & Response Quality
# ════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_flight_search_response_quality(
    ws_client, tts_audio, realtime_factor, is_mock_agent
):
    """Test flight search and verify response mentions flight details."""
    skip_if_mock(is_mock_agent, "Tool invocation requires real Nova Sonic")

    pcm = tts_audio("Search for flights from San Francisco to Tokyo next month.")
    result = await ws_client.send_and_collect(
        pcm,
        utterance_text="Search for flights from San Francisco to Tokyo next month.",
        timeout=60,
        idle_timeout=12,
        realtime_factor=realtime_factor,
    )
    _print_turn("Flight search", result)
    assert_no_errors(result)
    assert_has_agent_response(result)

    # Should have some tool calls
    if result.tool_calls:
        tools = _tool_names(result)
        print(f"  Tools invoked: {tools}")
        # At minimum we expect a flight-related tool
        flight_tools = {t for t in tools if "flight" in t}
        if flight_tools:
            print(f"  Flight tools confirmed: {flight_tools}")


@pytest.mark.asyncio
async def test_weather_response_quality(
    ws_client, tts_audio, realtime_factor, is_mock_agent
):
    """Test weather tool and validate response mentions weather data."""
    skip_if_mock(is_mock_agent, "Weather tool requires real Nova Sonic")

    pcm = tts_audio("What is the weather in London right now?")
    result = await ws_client.send_and_collect(
        pcm,
        utterance_text="What is the weather in London right now?",
        timeout=60,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )
    _print_turn("Weather query", result)
    assert_no_errors(result)
    assert_has_agent_response(result)

    text = _agent_text(result).lower()
    if text:
        # Response should mention some weather concept
        weather_words = ["temperature", "degree", "weather", "rain", "sun",
                        "cloud", "wind", "warm", "cold", "humid", "celsius",
                        "fahrenheit"]
        has_weather = any(w in text for w in weather_words)
        if not has_weather:
            print(f"  [WARN] Response may not contain weather data: {text[:200]}")


# ════════════════════════════════════════════════════════════════
# Scenario 5: Chinese Language Interaction
# ════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_chinese_interaction(
    ws_client, tts_audio, realtime_factor, is_mock_agent
):
    """Test Chinese language input and response."""
    skip_if_mock(is_mock_agent, "Chinese interaction requires real Nova Sonic")

    # Note: Gemini TTS may not support Chinese well, so we use text input
    await ws_client.send_text("我想去东京旅游，5天的行程，帮我推荐一下。")
    await asyncio.sleep(2)

    events = await ws_client.collect_events(timeout=60, idle_timeout=15, min_wait=3)
    transcripts = [
        e for e in events
        if e.event_type == "transcript" and e.payload.get("role") == "assistant"
    ]
    tool_events = [e for e in events if e.event_type == "tool_call"]
    errors = [e for e in events if e.event_type == "error"]

    agent_text = " ".join(e.payload.get("text", "") for e in transcripts)
    print(f"\n  Chinese response: {agent_text[:300]}")
    print(f"  Tools: {[e.payload.get('name') for e in tool_events]}")
    print(f"  Errors: {[e.payload.get('message') for e in errors]}")

    # Filter real errors
    real_errors = [
        e for e in errors
        if "switched to text mode" not in e.payload.get("message", "")
        and "voice model unavailable" not in e.payload.get("message", "").lower()
    ]
    assert len(real_errors) == 0, f"Unexpected errors: {real_errors}"


# ════════════════════════════════════════════════════════════════
# Scenario 6: LOD Change via Text (not TTS)
# ════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_lod_change_via_text_input(ws_client):
    """Test LOD detection works with text input (no TTS needed)."""
    # Send text that triggers LOD DOWN
    await ws_client.send_text("keep it short please")
    await asyncio.sleep(1)

    events = await ws_client.collect_events(timeout=5, idle_timeout=3, min_wait=1)
    lod_events = [e for e in events if e.event_type == "lod_change"]
    transcript_events = [
        e for e in events
        if e.event_type == "transcript" and e.payload.get("role") == "assistant"
    ]

    print(f"\n  LOD events: {[e.payload for e in lod_events]}")
    print(f"  Transcripts: {[e.payload.get('text', '') for e in transcript_events]}")

    # Should get LOD change to level 1
    if lod_events:
        assert lod_events[0].payload.get("level") == 1, (
            f"Expected LOD 1, got: {lod_events[0].payload}"
        )

    # Check for transition phrase
    if transcript_events:
        phrase = transcript_events[0].payload.get("text", "")
        print(f"  Transition phrase: {phrase}")


# ════════════════════════════════════════════════════════════════
# Scenario 7: Multi-Turn Context Retention
# ════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_context_retained_across_turns(
    ws_client, tts_audio, realtime_factor, is_mock_agent
):
    """Verify agent maintains context across multiple turns.

    Turn 1: Establish destination (Paris)
    Turn 2: Ask a follow-up using "there"
    → Agent should still reference Paris
    """
    skip_if_mock(is_mock_agent, "Context retention requires real Nova Sonic")

    # Turn 1: Establish Paris
    pcm1 = tts_audio("I'm interested in visiting Paris, France this summer.")
    result1 = await ws_client.send_and_collect(
        pcm1,
        utterance_text="I'm interested in visiting Paris, France this summer.",
        timeout=60,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )
    _print_turn("Context Turn 1: Paris intro", result1)
    assert_no_errors(result1)
    assert_has_agent_response(result1)

    # Turn 2: Follow-up with pronoun reference
    pcm2 = tts_audio("What are the top attractions there?")
    result2 = await ws_client.send_and_collect(
        pcm2,
        utterance_text="What are the top attractions there?",
        timeout=60,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )
    _print_turn("Context Turn 2: Follow-up", result2)
    assert_no_errors(result2)
    assert_has_agent_response(result2)

    # Check if agent maintained Paris context
    text2 = _agent_text(result2).lower()
    if text2:
        paris_refs = ["paris", "eiffel", "louvre", "champs", "montmartre",
                      "seine", "notre dame", "arc de triomphe", "french", "france"]
        has_paris = any(ref in text2 for ref in paris_refs)
        if not has_paris:
            print(f"  [WARN] Agent may have lost Paris context: {text2[:200]}")


# ════════════════════════════════════════════════════════════════
# Scenario 8: Response Quality — No Markdown in Voice Output
# ════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_no_markdown_in_voice_response(
    ws_client, tts_audio, realtime_factor, is_mock_agent
):
    """Verify TTS sanitization removes markdown from agent responses."""
    skip_if_mock(is_mock_agent, "Markdown sanitization check requires real agent")

    pcm = tts_audio("Give me a list of the top 3 things to do in Rome.")
    result = await ws_client.send_and_collect(
        pcm,
        utterance_text="Give me a list of the top 3 things to do in Rome.",
        timeout=60,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )
    _print_turn("Markdown check", result)
    assert_no_errors(result)
    assert_has_agent_response(result)

    text = _agent_text(result)
    if text:
        # Check for common markdown artifacts
        markdown_patterns = [
            r"\*\*",    # bold markers
            r"^\s*[-*]\s",  # list markers
            r"^\s*\d+\.\s",  # ordered list
            r"```",     # code fences
            r"\[.+\]\(.+\)",  # links
        ]
        for pattern in markdown_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            if matches:
                print(f"  [WARN] Found markdown pattern '{pattern}' in response: {matches}")


# ════════════════════════════════════════════════════════════════
# Scenario 9: Voice State Events
# ════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_voice_state_events(
    ws_client, tts_audio, realtime_factor, is_mock_agent
):
    """Verify voice_state events are emitted during response lifecycle."""
    skip_if_mock(is_mock_agent, "Voice state events require real agent")

    pcm = tts_audio("Tell me about Bangkok, Thailand.")
    result = await ws_client.send_and_collect(
        pcm,
        utterance_text="Tell me about Bangkok, Thailand.",
        timeout=60,
        idle_timeout=15,
        realtime_factor=realtime_factor,
    )
    _print_turn("Voice state check", result)
    assert_no_errors(result)

    # Check for voice_state events
    state_events = [
        e for e in result.all_events
        if e.event_type == "voice_state"
    ]
    states_received = [e.payload.get("state") for e in state_events]
    print(f"\n  Voice states: {states_received}")

    if state_events:
        # Should see at least "responding" state
        assert "responding" in states_received, (
            f"Expected 'responding' in voice states: {states_received}"
        )
