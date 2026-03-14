"""WebSocket voice bridge for NovaTour.

Bridges browser WebSocket ↔ BidiAgent for bidirectional voice streaming.
Handles: audio forwarding, transcript events, tool call events, errors.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.lod.controller import detect_lod_change, detect_lod_signal, get_lod_transition_phrase
from app.lod.intent import IntentType, rule_based_intent_classification
from app.lod.prompt_builder import build_system_prompt
from app.lod.state import LODState
from app.utils.resilience import is_recoverable
from app.utils.tts_sanitize import sanitize_for_tts
from app.voice.sonic_agent import MockAgent, MockTranscriptEvent, create_voice_agent
from app.voice.voice_state import VoiceStateMachine

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
            role = getattr(event, "role", "assistant")
            # Sanitize assistant text for TTS (strip markdown)
            if role == "assistant":
                text = sanitize_for_tts(text)
            return {
                "type": "transcript",
                "text": text,
                "role": role,
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


def _enrich_itinerary_coords(
    result: Dict, places_cache: Dict[str, Dict]
) -> Dict:
    """Enrich itinerary activities with coordinates and photo URLs from places_cache."""
    itinerary = result.get("itinerary", [])
    if not itinerary:
        return result

    for day in itinerary:
        for activity in day.get("activities", []):
            location = activity.get("location", "")
            activity_name = activity.get("activity", "")
            # Try matching on location name or activity name
            cached = None
            for search_key in [location, activity_name]:
                if not search_key:
                    continue
                cached = places_cache.get(search_key)
                if not cached:
                    for name, data in places_cache.items():
                        if name in search_key or search_key in name:
                            cached = data
                            break
                if cached:
                    break

            if cached:
                if "latitude" not in activity:
                    activity["latitude"] = cached["lat"]
                    activity["longitude"] = cached["lon"]
                if "photo_url" not in activity and "photo_url" in cached:
                    activity["photo_url"] = cached["photo_url"]

    return result


@router.websocket("/voice/{session_id}")
async def voice_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for voice conversations.

    Protocol:
    Client → Server:
        {"type": "audio", "data": "<base64 PCM 16kHz>"}
        {"type": "text", "text": "Hello"}
        {"type": "lod", "level": 1|2|3}

    Server → Client:
        {"type": "audio", "data": "<base64 PCM 24kHz>"}
        {"type": "transcript", "text": "...", "role": "user|assistant", "is_final": bool}
        {"type": "tool_call", "name": "...", "input": {...}, "status": "calling|complete"}
        {"type": "itinerary", "data": {...}}
        {"type": "interruption"}
        {"type": "error", "message": "..."}
        {"type": "lod_change", "level": 1|2|3}
        {"type": "voice_state", "state": "idle|responding|interrupted|finished"}
    """
    await websocket.accept()
    session_start = time.time()
    logger.info(f"WebSocket connected: session={session_id}")

    lod_state = LODState()
    voice_sm = VoiceStateMachine(session_id=session_id)
    places_cache: Dict[str, Dict] = {}  # name → {lat, lon}
    last_user_text: str = ""
    agent = create_voice_agent(session_id, lod_level=lod_state.current_lod)
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
            agent = create_voice_agent(session_id, lod_level=lod_state.current_lod)
            _active_sessions[session_id] = agent
            try:
                await agent.start()
            except Exception as retry_err:
                logger.warning(
                    f"BidiAgent retry failed: {retry_err}, falling back to MockAgent"
                )
                agent = MockAgent(
                    session_id=session_id,
                    system_prompt=build_system_prompt(lod_level=lod_state.current_lod),
                )
                _active_sessions[session_id] = agent
                await agent.start()
                await websocket.send_json({
                    "type": "error",
                    "message": f"Voice model unavailable ({retry_err}), switched to text mode.",
                })

        async def _handle_lod_change(old_lod: int, new_lod: int) -> None:
            """Send LOD change notification with transition phrase."""
            phrase = get_lod_transition_phrase(old_lod, new_lod)
            if phrase:
                await websocket.send_json({
                    "type": "transcript",
                    "text": phrase,
                    "role": "assistant",
                    "is_final": True,
                })
            await websocket.send_json(
                {"type": "lod_change", "level": new_lod}
            )

        async def forward_to_agent():
            """Forward client messages to the BidiAgent."""
            nonlocal agent, last_user_text
            while True:
                try:
                    raw = await websocket.receive_text()
                    data = json.loads(raw)
                    msg_type = data.get("type", "")

                    if msg_type == "audio":
                        # Forward audio to agent
                        if isinstance(agent, MockAgent):
                            await agent.send(data["data"])
                        else:
                            from strands.experimental.bidi import (
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

                    elif msg_type == "text":
                        text = data.get("text", "")
                        if text:
                            last_user_text = text

                            # Check for LOD change intent
                            old_lod = lod_state.current_lod
                            new_lod = detect_lod_change(text, old_lod)
                            if new_lod != old_lod:
                                lod_state.current_lod = new_lod
                                lod_state.increment_sequence()
                                await _handle_lod_change(old_lod, new_lod)

                            await agent.send(text)

                    elif msg_type == "lod":
                        # Explicit LOD change from UI
                        level = data.get("level", 2)
                        old_lod = lod_state.current_lod
                        lod_state.current_lod = max(1, min(3, level))
                        lod_state.increment_sequence()
                        if lod_state.current_lod != old_lod:
                            await _handle_lod_change(old_lod, lod_state.current_lod)
                        else:
                            await websocket.send_json(
                                {"type": "lod_change", "level": lod_state.current_lod}
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
                        evt_type = ws_event.get("type")

                        # Track voice state transitions
                        if evt_type == "audio":
                            old = voice_sm.state
                            voice_sm.on_audio_chunk()
                            if voice_sm.state != old:
                                await websocket.send_json(
                                    {"type": "voice_state", "state": voice_sm.state.value}
                                )

                        # Handle interruption — classify intent
                        if evt_type == "interruption":
                            voice_sm.on_interruption()
                            await websocket.send_json(
                                {"type": "voice_state", "state": voice_sm.state.value}
                            )
                            # Classify intent if we have recent user text
                            if last_user_text:
                                intent = rule_based_intent_classification(last_user_text)
                                if intent == IntentType.LOD_CHANGE:
                                    old_lod = lod_state.current_lod
                                    new_lod = detect_lod_change(last_user_text, old_lod)
                                    if new_lod != old_lod:
                                        lod_state.current_lod = new_lod
                                        lod_state.increment_sequence()
                                        await _handle_lod_change(old_lod, new_lod)

                        # Intercept search_places results → populate cache
                        if (
                            evt_type == "tool_call"
                            and ws_event.get("name") == "search_places"
                            and ws_event.get("status") == "complete"
                        ):
                            try:
                                result_str = ws_event.get("result", "{}")
                                result_data = json.loads(result_str)
                                for place in result_data.get("places", []):
                                    name = place.get("name", "")
                                    lat = place.get("latitude") or place.get("lat")
                                    lon = place.get("longitude") or place.get("lon") or place.get("lng")
                                    if name and lat and lon:
                                        entry = {"lat": float(lat), "lon": float(lon)}
                                        photo = place.get("photo_url", "")
                                        if photo:
                                            entry["photo_url"] = photo
                                        places_cache[name] = entry
                            except (json.JSONDecodeError, TypeError, ValueError):
                                pass

                        # Intercept itinerary data from tool results
                        if (
                            evt_type == "tool_call"
                            and ws_event.get("name") == "plan_itinerary"
                            and ws_event.get("status") == "complete"
                        ):
                            try:
                                result = json.loads(ws_event.get("result", "{}"))
                                if "itinerary" in result:
                                    # Enrich with cached coordinates
                                    result = _enrich_itinerary_coords(result, places_cache)
                                    await websocket.send_json(
                                        {"type": "itinerary", "data": result}
                                    )
                            except (json.JSONDecodeError, TypeError):
                                pass

                            # Mark response complete
                            voice_sm.on_response_complete()
                            await websocket.send_json(
                                {"type": "voice_state", "state": voice_sm.state.value}
                            )

                        await websocket.send_json(ws_event)
            except Exception as e:
                if is_recoverable(e):
                    logger.warning(
                        f"Recoverable error for session={session_id}: {e}, "
                        "falling back to MockAgent"
                    )
                    # Fall back to MockAgent and notify client
                    try:
                        await agent.stop()
                    except Exception:
                        pass
                    agent = MockAgent(
                        session_id=session_id,
                        system_prompt=build_system_prompt(lod_level=lod_state.current_lod),
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
                else:
                    logger.error(f"Non-recoverable error for session={session_id}: {e}")
                    raise

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
        # Cleanup — timeout-protected to prevent indefinite hang
        # (SDK's stop_all() awaits network I/O without timeout)
        try:
            await asyncio.wait_for(agent.stop(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(f"agent.stop() timed out for session={session_id}, forcing cleanup")
        except Exception:
            pass
        _active_sessions.pop(session_id, None)
        elapsed = time.time() - session_start
        logger.info(f"Session ended: {session_id} (duration={elapsed:.1f}s)")
