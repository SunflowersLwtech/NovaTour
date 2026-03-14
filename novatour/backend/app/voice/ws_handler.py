"""WebSocket voice bridge for NovaTour.

Bridges browser WebSocket ↔ BidiAgent for bidirectional voice streaming.
Handles: audio forwarding, transcript events, tool call events, errors.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.lod.controller import detect_lod_change
from app.lod.prompt_builder import build_system_prompt
from app.voice.sonic_agent import MockAgent, MockTranscriptEvent, create_voice_agent

logger = logging.getLogger(__name__)

router = APIRouter()

# Active sessions for cleanup
_active_sessions: Dict[str, Any] = {}


def _convert_bidi_event(event: Any) -> Optional[Dict[str, Any]]:
    """Convert a BidiAgent event to a WebSocket JSON message.

    Maps Strands BidiAgent events to our frontend protocol:
    - BidiAudioStreamEvent → {"type": "audio", "data": "<base64>"}
    - BidiTranscriptStreamEvent → {"type": "transcript", "text": "...", ...}
    - ToolUseStreamEvent → {"type": "tool_call", "name": "...", ...}
    - MockTranscriptEvent → {"type": "transcript", ...}
    """
    event_type = type(event).__name__

    # Mock agent events
    if isinstance(event, MockTranscriptEvent):
        return {
            "type": "transcript",
            "text": event.text,
            "role": event.role,
            "is_final": event.is_final,
        }

    # BidiAgent audio output
    if event_type == "BidiAudioStreamEvent" or hasattr(event, "audio"):
        audio_data = getattr(event, "audio", None) or getattr(event, "data", None)
        if audio_data:
            return {"type": "audio", "data": audio_data}

    # BidiAgent transcript
    if event_type == "BidiTranscriptStreamEvent" or hasattr(event, "text"):
        text = getattr(event, "text", "")
        if text:
            return {
                "type": "transcript",
                "text": text,
                "role": getattr(event, "role", "assistant"),
                "is_final": getattr(event, "is_final", False),
            }

    # Tool use events
    if event_type in ("ToolUseStreamEvent", "ToolResultStreamEvent") or hasattr(
        event, "tool_name"
    ):
        return {
            "type": "tool_call",
            "name": getattr(event, "tool_name", getattr(event, "name", "unknown")),
            "input": getattr(event, "input", {}),
            "status": "complete"
            if event_type == "ToolResultStreamEvent"
            else "calling",
            "result": str(getattr(event, "result", ""))[:500]
            if event_type == "ToolResultStreamEvent"
            else None,
        }

    # Content end / interruption
    if event_type == "BidiContentEndEvent":
        stop_reason = getattr(event, "stop_reason", "")
        if stop_reason == "INTERRUPTED":
            return {"type": "interruption"}

    # Usage events — log but don't forward
    if event_type == "BidiUsageEvent":
        usage = getattr(event, "usage", None)
        if usage:
            logger.info(f"Token usage: {usage}")
        return None

    # Connection restart — notify client
    if event_type == "BidiConnectionRestartEvent":
        return {
            "type": "error",
            "message": "Voice connection is reconnecting, please wait...",
        }

    return None


@router.websocket("/voice/{session_id}")
async def voice_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for voice conversations.

    Protocol:
    Client → Server:
        {"type": "audio", "data": "<base64 PCM 16kHz>"}
        {"type": "text", "text": "Hello"}
        {"type": "lod", "level": 1|2|3}

    Server → Client:
        {"type": "audio", "data": "<base64 PCM 16kHz>"}
        {"type": "transcript", "text": "...", "role": "user|assistant", "is_final": bool}
        {"type": "tool_call", "name": "...", "input": {...}, "status": "calling|complete"}
        {"type": "itinerary", "data": {...}}
        {"type": "interruption"}
        {"type": "error", "message": "..."}
        {"type": "lod_change", "level": 1|2|3}
    """
    await websocket.accept()
    logger.info(f"WebSocket connected: session={session_id}")

    current_lod = 2
    agent = create_voice_agent(session_id, lod_level=current_lod)
    _active_sessions[session_id] = agent

    try:
        # Start agent with retry — if BidiAgent fails, retry once before MockAgent fallback
        try:
            await agent.start()
        except Exception as start_err:
            logger.warning(
                f"BidiAgent start failed: {start_err}, retrying once..."
            )
            try:
                await agent.stop()
            except Exception:
                pass
            agent = create_voice_agent(session_id, lod_level=current_lod)
            _active_sessions[session_id] = agent
            try:
                await agent.start()
            except Exception as retry_err:
                logger.warning(
                    f"BidiAgent retry failed: {retry_err}, falling back to MockAgent"
                )
                agent = MockAgent(
                    session_id=session_id,
                    system_prompt=build_system_prompt(lod_level=current_lod),
                )
                _active_sessions[session_id] = agent
                await agent.start()
                await websocket.send_json({
                    "type": "error",
                    "message": f"Voice model unavailable ({retry_err}), switched to text mode.",
                })

        async def forward_to_agent():
            """Forward client messages to the BidiAgent."""
            nonlocal current_lod, agent
            while True:
                try:
                    raw = await websocket.receive_text()
                    data = json.loads(raw)
                    msg_type = data.get("type", "")

                    if msg_type == "audio":
                        # Forward audio to agent
                        try:
                            from strands.experimental.bidi.events import (
                                BidiAudioInputEvent,
                            )

                            await agent.send(
                                BidiAudioInputEvent(
                                    audio=data["data"],
                                    format="pcm",
                                    sample_rate=16000,
                                    channels=1,
                                )
                            )
                        except ImportError:
                            # MockAgent - just send raw
                            await agent.send(data["data"])

                    elif msg_type == "text":
                        text = data.get("text", "")
                        if text:
                            # Check for LOD change intent
                            new_lod = detect_lod_change(text, current_lod)
                            if new_lod != current_lod:
                                current_lod = new_lod
                                await websocket.send_json(
                                    {"type": "lod_change", "level": current_lod}
                                )

                            await agent.send(text)

                    elif msg_type == "lod":
                        # Explicit LOD change from UI
                        level = data.get("level", 2)
                        current_lod = max(1, min(3, level))
                        await websocket.send_json(
                            {"type": "lod_change", "level": current_lod}
                        )

                except WebSocketDisconnect:
                    raise
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client: session={session_id}")
                except Exception as e:
                    logger.error(f"Error forwarding to agent: {e}")

        async def forward_to_client():
            """Forward BidiAgent events to the client."""
            nonlocal agent
            try:
                async for event in agent.receive():
                    ws_event = _convert_bidi_event(event)
                    if ws_event:
                        # Intercept itinerary data from tool results
                        if (
                            ws_event.get("type") == "tool_call"
                            and ws_event.get("name") == "plan_itinerary"
                            and ws_event.get("status") == "complete"
                        ):
                            try:
                                result = json.loads(ws_event.get("result", "{}"))
                                if "itinerary" in result:
                                    await websocket.send_json(
                                        {"type": "itinerary", "data": result}
                                    )
                            except (json.JSONDecodeError, TypeError):
                                pass

                        await websocket.send_json(ws_event)
            except Exception as e:
                if "disconnect" not in str(e).lower():
                    logger.warning(
                        f"BidiAgent error for session={session_id}: {e}, "
                        "falling back to MockAgent"
                    )
                    # Fall back to MockAgent and notify client
                    try:
                        await agent.stop()
                    except Exception:
                        pass
                    agent = MockAgent(
                        session_id=session_id,
                        system_prompt=build_system_prompt(lod_level=current_lod),
                    )
                    _active_sessions[session_id] = agent
                    await agent.start()
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Voice model unavailable ({e}), switched to text mode.",
                    })
                    # Continue receiving from MockAgent
                    async for event in agent.receive():
                        ws_event = _convert_bidi_event(event)
                        if ws_event:
                            await websocket.send_json(ws_event)

        # Run both directions concurrently; cancel remaining if one finishes
        tasks = [
            asyncio.create_task(forward_to_agent()),
            asyncio.create_task(forward_to_client()),
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        # Re-raise any exceptions from completed tasks
        for t in done:
            if t.exception() and not isinstance(t.exception(), asyncio.CancelledError):
                raise t.exception()

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: session={session_id}, error={e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        # Cleanup
        try:
            await agent.stop()
        except Exception:
            pass
        _active_sessions.pop(session_id, None)
        logger.info(f"Session cleaned up: {session_id}")
