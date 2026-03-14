"""Tests for NovaTour voice pipeline (Phase 3).

Tests MockAgent, event conversion, agent factory, and HTTP endpoints.
WebSocket integration tests are marked separately (need real async WS client).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.voice.sonic_agent import MockAgent, MockTranscriptEvent, create_voice_agent
from app.voice.ws_handler import _convert_bidi_event


# ── MockAgent Tests ──────────────────────────────────────────


def test_mock_agent_creation():
    agent = MockAgent(session_id="test", system_prompt="Test prompt")
    assert agent.session_id == "test"
    assert agent._running is False


@pytest.mark.asyncio
async def test_mock_agent_lifecycle():
    agent = MockAgent(session_id="test", system_prompt="Test prompt")
    await agent.start()
    assert agent._running is True
    await agent.stop()
    assert agent._running is False


@pytest.mark.asyncio
async def test_mock_agent_receive():
    """MockAgent should yield greeting on start, then respond to send()."""
    agent = MockAgent(session_id="test", system_prompt="Test prompt")
    await agent.start()
    # Collect the greeting event
    events = []
    async for event in agent.receive():
        events.append(event)
        if len(events) >= 1:
            await agent.stop()
            break
    assert len(events) >= 1
    assert "NovaTour" in events[0].text
    assert events[0].role == "assistant"


@pytest.mark.asyncio
async def test_mock_agent_send_and_receive():
    """MockAgent should produce response after send()."""
    agent = MockAgent(session_id="test", system_prompt="Test prompt")
    await agent.start()

    # Send a message
    await agent.send("Hello there")

    # Collect events (greeting + response)
    events = []
    async for event in agent.receive():
        events.append(event)
        if len(events) >= 2:
            await agent.stop()
            break

    assert len(events) >= 2
    assert "NovaTour" in events[0].text  # greeting
    assert "Mock" in events[1].text  # response to send


# ── Event Conversion Tests ───────────────────────────────────


def test_convert_mock_transcript():
    event = MockTranscriptEvent(text="Hello", role="assistant", is_final=True)
    result = _convert_bidi_event(event)
    assert result["type"] == "transcript"
    assert result["text"] == "Hello"
    assert result["role"] == "assistant"
    assert result["is_final"] is True


def test_convert_unknown_event_returns_none():
    result = _convert_bidi_event(object())
    assert result is None


# ── Agent Factory Tests ──────────────────────────────────────


def test_create_voice_agent_returns_mock_or_bidi():
    """create_voice_agent should return an agent (mock fallback is OK)."""
    agent = create_voice_agent("test-session", lod_level=2)
    assert agent is not None
    assert hasattr(agent, "start")
    assert hasattr(agent, "stop")
    assert hasattr(agent, "send")
    assert hasattr(agent, "receive")


def test_create_voice_agent_different_lod():
    """Agent creation works with all LOD levels."""
    for lod in (1, 2, 3):
        agent = create_voice_agent(f"test-{lod}", lod_level=lod)
        assert agent is not None


# ── HTTP Endpoint Tests ──────────────────────────────────────


def test_health_endpoint():
    """Test health check endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "NovaTour"


def test_ws_route_registered():
    """Verify the WebSocket route is registered in the app."""
    routes = [r.path for r in app.routes]
    assert "/ws/voice/{session_id}" in routes
