"""Validation helpers for NovaTour E2E tests.

Provides assertion functions for checking transcripts, tool calls,
audio output, LOD changes, and other response properties.
"""

from __future__ import annotations

import base64
from typing import Any

from .ws_client import TurnResult


def assert_has_agent_response(result: TurnResult, msg: str = ""):
    """Assert that the agent produced at least one response (transcript or audio)."""
    has_transcript = len(result.agent_transcripts) > 0
    has_audio = len(result.audio_chunks) > 0
    assert has_transcript or has_audio, (
        f"No agent response received. "
        f"Transcripts: {result.agent_transcripts}, "
        f"Audio chunks: {len(result.audio_chunks)}. {msg}"
    )


def assert_user_transcript_contains(result: TurnResult, keyword: str, case_sensitive: bool = False):
    """Assert that the user transcript contains a keyword."""
    all_text = " ".join(result.user_transcripts)
    if not case_sensitive:
        all_text = all_text.lower()
        keyword = keyword.lower()
    assert keyword in all_text, (
        f"Expected '{keyword}' in user transcripts, got: {result.user_transcripts}"
    )


def assert_agent_transcript_contains(result: TurnResult, keyword: str, case_sensitive: bool = False):
    """Assert that the agent transcript contains a keyword."""
    all_text = " ".join(result.agent_transcripts)
    if not case_sensitive:
        all_text = all_text.lower()
        keyword = keyword.lower()
    assert keyword in all_text, (
        f"Expected '{keyword}' in agent transcripts, got: {result.agent_transcripts}"
    )


def assert_tool_called(result: TurnResult, tool_name: str) -> dict[str, Any]:
    """Assert that a specific tool was called and return its event."""
    matching = [tc for tc in result.tool_calls if tc.get("name") == tool_name]
    assert len(matching) > 0, (
        f"Expected tool '{tool_name}' to be called. "
        f"Tool calls: {[tc.get('name') for tc in result.tool_calls]}"
    )
    return matching[0]


def assert_tool_completed(result: TurnResult, tool_name: str) -> dict[str, Any]:
    """Assert a tool was called and completed successfully."""
    matching = [
        tc for tc in result.tool_calls
        if tc.get("name") == tool_name and tc.get("status") == "complete"
    ]
    assert len(matching) > 0, (
        f"Expected tool '{tool_name}' to complete. "
        f"Tool calls: {[(tc.get('name'), tc.get('status')) for tc in result.tool_calls]}"
    )
    return matching[0]


def assert_audio_output_valid(result: TurnResult, min_chunks: int = 1):
    """Assert the agent returned valid base64-encoded audio."""
    assert len(result.audio_chunks) >= min_chunks, (
        f"Expected at least {min_chunks} audio chunks, got {len(result.audio_chunks)}"
    )
    for i, chunk in enumerate(result.audio_chunks[:3]):  # check first 3
        try:
            decoded = base64.b64decode(chunk)
            assert len(decoded) > 0, f"Audio chunk {i} decoded to empty bytes"
            assert len(decoded) % 2 == 0, f"Audio chunk {i} has odd byte count (not 16-bit PCM)"
        except Exception as e:
            raise AssertionError(f"Audio chunk {i} is not valid base64: {e}")


def assert_lod_changed(result: TurnResult, expected_level: int):
    """Assert that a LOD change event was received with the expected level."""
    assert expected_level in result.lod_changes, (
        f"Expected LOD change to level {expected_level}, got: {result.lod_changes}"
    )


def assert_itinerary_received(result: TurnResult):
    """Assert that an itinerary event was received."""
    assert len(result.itineraries) > 0, "Expected itinerary event, got none"


def assert_no_errors(result: TurnResult):
    """Assert no unexpected error events were received.

    Tolerates the BidiAgent→MockAgent fallback notification, which is
    an expected informational message when Nova Sonic is unavailable.
    """
    real_errors = [
        e for e in result.errors
        if "switched to text mode" not in e and "voice model unavailable" not in e.lower()
    ]
    assert len(real_errors) == 0, f"Unexpected errors: {real_errors}"


def assert_response_latency(result: TurnResult, max_seconds: float = 15.0):
    """Assert first response came within acceptable latency."""
    assert result.first_response_latency is not None, "No response latency measured"
    assert result.first_response_latency <= max_seconds, (
        f"Response latency {result.first_response_latency:.2f}s exceeds {max_seconds}s"
    )


def assert_connection_alive(result: TurnResult):
    """Assert the connection is still alive (got any events at all)."""
    assert len(result.all_events) > 0, "No events received — connection may be dead"


def assert_no_prompt_leak(result: TurnResult, markers: list[str]):
    """Assert that no system prompt markers appear in agent transcripts.

    Checks all agent transcript text against a list of known markers
    from the system prompt that should never be exposed to users.
    """
    all_text = " ".join(result.agent_transcripts)
    leaked = [m for m in markers if m.lower() in all_text.lower()]
    assert len(leaked) == 0, (
        f"System prompt leaked! Found markers: {leaked}\n"
        f"Agent response: {all_text[:500]}"
    )
