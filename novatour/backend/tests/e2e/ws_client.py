"""WebSocket test client for NovaTour E2E testing.

Connects to the NovaTour WebSocket endpoint, streams audio chunks,
and collects all server events for validation.
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

import websockets


@dataclass
class CollectedEvent:
    """A single event received from the server with timing info."""
    timestamp: float  # monotonic time
    event_type: str
    payload: dict[str, Any]


@dataclass
class TurnResult:
    """Aggregated results from a single conversation turn."""
    utterance: str
    user_transcripts: list[str] = field(default_factory=list)
    agent_transcripts: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    audio_chunks: list[str] = field(default_factory=list)  # base64 audio
    lod_changes: list[int] = field(default_factory=list)
    itineraries: list[dict[str, Any]] = field(default_factory=list)
    interruptions: int = 0
    errors: list[str] = field(default_factory=list)
    first_response_latency: Optional[float] = None
    all_events: list[CollectedEvent] = field(default_factory=list)


# Default chunk size: 80ms at 16kHz, 16-bit mono = 2560 bytes
CHUNK_SIZE_BYTES = int(16000 * 0.08) * 2  # 2560 bytes
REALTIME_FACTOR = 1.0  # 1.0 = real-time speed


class NovaTourWSClient:
    """WebSocket client that streams audio and collects server events."""

    def __init__(self, server_url: str, session_id: Optional[str] = None):
        self.server_url = server_url.rstrip("/")
        self.session_id = session_id or f"e2e_{uuid.uuid4().hex[:8]}"
        self.ws_url = f"{self.server_url}/ws/voice/{self.session_id}"
        self._ws: Optional[websockets.ClientConnection] = None
        self._recv_task: Optional[asyncio.Task] = None
        self._events: asyncio.Queue[CollectedEvent] = asyncio.Queue()

    async def connect(self):
        """Open WebSocket connection."""
        self._ws = await websockets.connect(self.ws_url, max_size=10 * 1024 * 1024)
        self._recv_task = asyncio.create_task(self._receiver_loop())

    async def disconnect(self):
        """Close WebSocket connection."""
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def _receiver_loop(self):
        """Background task that collects all incoming events."""
        try:
            async for message in self._ws:
                now = time.monotonic()
                try:
                    data = json.loads(message)
                    event = CollectedEvent(
                        timestamp=now,
                        event_type=data.get("type", "unknown"),
                        payload=data,
                    )
                    await self._events.put(event)
                except json.JSONDecodeError:
                    await self._events.put(CollectedEvent(
                        timestamp=now,
                        event_type="raw",
                        payload={"raw": str(message)},
                    ))
        except websockets.ConnectionClosed:
            pass
        except asyncio.CancelledError:
            pass

    async def send_audio(
        self,
        pcm_bytes: bytes,
        chunk_size: int = CHUNK_SIZE_BYTES,
        realtime_factor: float = REALTIME_FACTOR,
    ):
        """Stream PCM audio in chunks over WebSocket as base64 JSON messages."""
        for offset in range(0, len(pcm_bytes), chunk_size):
            chunk = pcm_bytes[offset:offset + chunk_size]
            if not chunk:
                continue
            b64 = base64.b64encode(chunk).decode("ascii")
            try:
                await self._ws.send(json.dumps({"type": "audio", "data": b64}))
            except websockets.ConnectionClosed:
                # Connection may close during agent fallback — stop sending
                break

            if realtime_factor > 0:
                chunk_duration = (len(chunk) / 2.0) / 16000.0  # 16-bit mono 16kHz
                await asyncio.sleep(chunk_duration / realtime_factor)

    async def send_text(self, text: str):
        """Send a text message over WebSocket."""
        await self._ws.send(json.dumps({"type": "text", "text": text}))

    async def send_lod(self, level: int):
        """Send an explicit LOD change over WebSocket."""
        await self._ws.send(json.dumps({"type": "lod", "level": level}))

    async def send_raw(self, data: str):
        """Send raw string data (for error testing)."""
        await self._ws.send(data)

    async def collect_events(
        self,
        timeout: float = 30.0,
        idle_timeout: float = 5.0,
        min_wait: float = 2.0,
    ) -> list[CollectedEvent]:
        """Collect events until idle or timeout.

        Args:
            timeout: Maximum total wait time in seconds.
            idle_timeout: Stop if no events for this many seconds.
            min_wait: Minimum time to wait before considering idle.

        Returns:
            List of collected events.
        """
        events = []
        start = time.monotonic()
        last_event_time = start

        while True:
            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                break

            since_last = time.monotonic() - last_event_time
            if since_last >= idle_timeout and (time.monotonic() - start) >= min_wait:
                break

            try:
                remaining = min(timeout - elapsed, idle_timeout - since_last, 1.0)
                event = await asyncio.wait_for(self._events.get(), timeout=max(0.1, remaining))
                events.append(event)
                last_event_time = time.monotonic()
            except asyncio.TimeoutError:
                continue

        return events

    async def send_and_collect(
        self,
        pcm_bytes: bytes,
        utterance_text: str = "",
        timeout: float = 30.0,
        idle_timeout: float = 5.0,
        realtime_factor: float = REALTIME_FACTOR,
    ) -> TurnResult:
        """Stream audio, then collect and categorize all response events."""
        # Drain any pending events from previous turns
        while not self._events.empty():
            try:
                self._events.get_nowait()
            except asyncio.QueueEmpty:
                break

        send_start = time.monotonic()
        await self.send_audio(pcm_bytes, realtime_factor=realtime_factor)
        events = await self.collect_events(timeout=timeout, idle_timeout=idle_timeout)

        return self._categorize_events(events, utterance_text, send_start)

    @staticmethod
    def _categorize_events(
        events: list[CollectedEvent],
        utterance: str,
        send_start: float,
    ) -> TurnResult:
        result = TurnResult(utterance=utterance)
        result.all_events = events

        for event in events:
            payload = event.payload
            etype = event.event_type

            if etype == "transcript":
                role = payload.get("role", "")
                text = payload.get("text", "")
                if role == "user":
                    result.user_transcripts.append(text)
                elif role == "assistant":
                    result.agent_transcripts.append(text)
                    if result.first_response_latency is None:
                        result.first_response_latency = event.timestamp - send_start

            elif etype == "audio":
                result.audio_chunks.append(payload.get("data", ""))
                if result.first_response_latency is None:
                    result.first_response_latency = event.timestamp - send_start

            elif etype == "tool_call":
                result.tool_calls.append(payload)

            elif etype == "lod_change":
                result.lod_changes.append(payload.get("level", 0))

            elif etype == "itinerary":
                result.itineraries.append(payload.get("data", {}))

            elif etype == "interruption":
                result.interruptions += 1

            elif etype == "error":
                result.errors.append(payload.get("message", ""))

        return result
