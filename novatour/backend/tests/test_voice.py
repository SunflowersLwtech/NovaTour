"""Tests for NovaTour voice pipeline (Phase 3).

Tests MockAgent, event conversion, agent factory, and HTTP endpoints.
WebSocket integration tests are marked separately (need real async WS client).
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from strands.types._events import ToolResultEvent, ToolUseStreamEvent

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


def test_convert_tool_use_event():
    event = ToolUseStreamEvent(
        delta={"toolUse": {"name": "plan_itinerary"}},
        current_tool_use={
            "toolUseId": "tool-123",
            "name": "plan_itinerary",
            "input": {"destination": "Seoul", "days": 3},
        },
    )

    result = _convert_bidi_event(event)
    assert result["type"] == "tool_call"
    assert result["tool_use_id"] == "tool-123"
    assert result["name"] == "plan_itinerary"
    assert result["input"] == {"destination": "Seoul", "days": 3}
    assert result["status"] == "calling"


def test_convert_tool_result_event():
    event = ToolResultEvent(
        {
            "toolUseId": "tool-123",
            "status": "success",
            "content": [{"json": {"destination": "Seoul", "days": 3}}],
        }
    )

    result = _convert_bidi_event(event)
    assert result["type"] == "tool_call"
    assert result["tool_use_id"] == "tool-123"
    assert result["status"] == "complete"
    assert result["result"] == '{"destination": "Seoul", "days": 3}'


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


class StubVoiceAgent:
    """Simple async agent stub for websocket session tests."""

    def __init__(
        self,
        reply_text: str = "ack",
        receive_error: Exception | None = None,
        event_factory=None,
    ):
        self.reply_text = reply_text
        self.receive_error = receive_error
        self.event_factory = event_factory
        self.start_calls = 0
        self.stop_calls = 0
        self.sent_messages: list[object] = []
        self._queue: asyncio.Queue = asyncio.Queue()

    async def start(self):
        self.start_calls += 1

    async def stop(self):
        self.stop_calls += 1
        self._queue.put_nowait(None)

    async def send(self, data):
        self.sent_messages.append(data)
        if self.receive_error is None:
            if self.event_factory is not None:
                self._queue.put_nowait(self.event_factory())
            else:
                self._queue.put_nowait(
                    MockTranscriptEvent(text=self.reply_text, role="assistant", is_final=True)
                )

    async def receive(self):
        if self.receive_error is not None:
            raise self.receive_error
        while True:
            event = await self._queue.get()
            if event is None:
                break
            yield event


def test_ws_lazy_starts_voice_agent(monkeypatch):
    """Connecting should not start the provider session before the first real input."""
    agents: list[StubVoiceAgent] = []

    def fake_create_voice_agent(session_id: str, lod_level: int = 2):
        agent = StubVoiceAgent(reply_text=f"reply-{session_id}-{lod_level}")
        agents.append(agent)
        return agent

    monkeypatch.setattr("app.voice.ws_handler.create_voice_agent", fake_create_voice_agent)

    client = TestClient(app)
    with client.websocket_connect("/ws/voice/lazy-start") as websocket:
        websocket.send_json({"type": "lod", "level": 3})
        assert len(agents) == 0
        lod_event = websocket.receive_json()
        assert lod_event["type"] == "transcript"
        lod_change_event = websocket.receive_json()
        assert lod_change_event["type"] == "lod_change"
        assert lod_change_event["level"] == 3

        websocket.send_json({"type": "text", "text": "hello"})
        event = None
        for _ in range(3):
            candidate = websocket.receive_json()
            if candidate["type"] == "transcript":
                event = candidate
                break

        assert len(agents) == 1
        assert agents[0].start_calls == 1
        assert agents[0].sent_messages == ["hello"]
        assert event is not None
        assert event["type"] == "transcript"
        assert event["text"] == "reply-lazy-start-3"

    assert agents[0].stop_calls >= 1


def test_ws_restarts_idle_voice_session_before_next_turn(monkeypatch):
    """An idle session should be recreated cleanly instead of falling back to text mode."""
    agents = [StubVoiceAgent("first-turn"), StubVoiceAgent("second-turn")]

    def fake_create_voice_agent(session_id: str, lod_level: int = 2):
        return agents.pop(0)

    monkeypatch.setattr("app.voice.ws_handler.create_voice_agent", fake_create_voice_agent)
    monkeypatch.setattr("app.voice.ws_handler._VOICE_IDLE_RESET_SECONDS", 0.01)

    client = TestClient(app)
    with client.websocket_connect("/ws/voice/idle-reset") as websocket:
        websocket.send_json({"type": "text", "text": "first"})
        first_event = websocket.receive_json()
        assert first_event["text"] == "first-turn"

        time.sleep(0.02)

        websocket.send_json({"type": "text", "text": "second"})
        second_event = websocket.receive_json()
        assert second_event["text"] == "second-turn"


def test_ws_swallows_provider_idle_timeout_and_recovers(monkeypatch):
    """Provider idle timeout should reset the session without surfacing a fallback error."""
    created_agents = [
        StubVoiceAgent(receive_error=RuntimeError(
            "Timed out waiting for audio bytes or interactive content"
        )),
        StubVoiceAgent(reply_text="recovered"),
    ]

    def fake_create_voice_agent(session_id: str, lod_level: int = 2):
        return created_agents.pop(0)

    monkeypatch.setattr("app.voice.ws_handler.create_voice_agent", fake_create_voice_agent)

    client = TestClient(app)
    with client.websocket_connect("/ws/voice/timeout-recovery") as websocket:
        websocket.send_json({"type": "text", "text": "first"})
        time.sleep(0.05)

        websocket.send_json({"type": "text", "text": "second"})
        event = websocket.receive_json()

        assert event["type"] == "transcript"
        assert event["text"] == "recovered"


def test_ws_announces_long_running_itinerary_tool(monkeypatch):
    """Long-running itinerary calls should emit an immediate assistant acknowledgement."""
    agent = StubVoiceAgent(
        event_factory=lambda: ToolUseStreamEvent(
            delta={"toolUse": {"name": "plan_itinerary"}},
            current_tool_use={
                "toolUseId": "tool-999",
                "name": "plan_itinerary",
                "input": {"destination": "Seoul, South Korea", "days": 3},
            },
        )
    )

    monkeypatch.setattr(
        "app.voice.ws_handler.create_voice_agent",
        lambda session_id, lod_level=2: agent,
    )

    client = TestClient(app)
    with client.websocket_connect("/ws/voice/itinerary-ack") as websocket:
        websocket.send_json({"type": "text", "text": "plan my trip"})
        event = websocket.receive_json()

        assert event["type"] == "transcript"
        assert "planning your itinerary for Seoul, South Korea" in event["text"]
