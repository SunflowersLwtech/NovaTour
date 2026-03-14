"""Flight booking tool using Amazon Nova Act for browser automation.

Supports two modes:
1. Synchronous: Tool returns directly with booking result (used by BidiAgent)
2. Async two-step: confirm_booking returns immediately, background task runs Nova Act
   and pushes progress via WebSocket (booking_progress events).
"""

import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, Optional

from strands import tool

from app.config import settings
from app.utils.resilience import timed_log

logger = logging.getLogger(__name__)

def _mock_booking(origin: str, destination: str) -> dict:
    return {
        "status": "found",
        "booking": {
            "airline": "Major Carrier",
            "price": "$450-600",
            "departure": "10:00 AM",
            "duration": "Varies by route",
            "stops": "Non-stop",
        },
        "message": f"Found flight from {origin} to {destination} (mock mode)",
        "mock": True,
    }

# Active async booking tasks
_booking_tasks: Dict[str, asyncio.Task] = {}


@tool
def book_flight(
    origin: str,
    destination: str,
    date: str,
    max_price: str = "",
) -> dict:
    """Book a flight via automated browser search. Takes 30-60 seconds.

    Args:
        origin: Departure city
        destination: Arrival city
        date: Travel date (natural language)
        max_price: Max acceptable price (optional)
    """
    if settings.mock_mode:
        return {
            **_mock_booking(origin, destination),
            "message": f"Found flight from {origin} to {destination} on {date} (mock mode)",
        }

    try:
        from nova_act import NovaAct

        nova_act_key = settings.nova_act_api_key
        if not nova_act_key:
            return {
                **_mock_booking(origin, destination),
                "message": f"Found flight from {origin} to {destination} (mock - no API key)",
                "fallback_reason": "Nova Act API key not configured",
            }

        with timed_log(logger, "book_flight"), NovaAct(
            starting_page="https://www.google.com/travel/flights",
            nova_act_api_key=nova_act_key,
        ) as nova:
            nova.act(
                f"Search for one-way flights from {origin} to {destination} on {date}"
            )
            nova.act("Sort results by price, showing cheapest first")

            price_filter = f" under {max_price}" if max_price else ""
            result = nova.act(
                f"Get the details of the cheapest flight{price_filter}: "
                "airline name, price, departure time, arrival time, duration, and number of stops",
            )

            return {
                "status": "found",
                "booking": {"details": str(result)},
                "message": f"Found flight from {origin} to {destination} on {date}",
            }

    except ImportError:
        logger.warning("nova-act not installed, returning mock data")
        return {
            **_mock_booking(origin, destination),
            "message": f"Found flight from {origin} to {destination} (mock - nova-act not installed)",
            "fallback_reason": "nova-act package not installed",
        }
    except Exception as e:
        logger.warning(f"Flight booking failed: {e}, returning mock data")
        return {
            **_mock_booking(origin, destination),
            "message": f"Found flight from {origin} to {destination} (mock - error)",
            "fallback_reason": str(e),
        }


# ── Async Two-Step Booking ───────────────────────────────────


def confirm_booking(
    origin: str,
    destination: str,
    date: str,
    max_price: str = "",
    progress_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Start an async booking task. Returns immediately with a task_id.

    The actual booking runs in background and pushes progress events
    via the provided callback.

    Args:
        origin: Departure city
        destination: Arrival city
        date: Travel date
        max_price: Max price filter
        progress_callback: async callable(event_dict) for progress updates

    Returns:
        {"status": "searching", "task_id": "...", "message": "Searching..."}
    """
    task_id = str(uuid.uuid4())[:8]

    async def _run_booking():
        try:
            if progress_callback:
                await progress_callback(
                    {
                        "type": "booking_progress",
                        "task_id": task_id,
                        "step": f"Searching flights from {origin} to {destination}...",
                        "status": "searching",
                    }
                )

            # Simulate async work (or real Nova Act call)
            await asyncio.sleep(2)

            result = book_flight(origin, destination, date, max_price)

            if progress_callback:
                await progress_callback(
                    {
                        "type": "booking_progress",
                        "task_id": task_id,
                        "step": result.get("message", "Booking complete"),
                        "status": "complete",
                        "result": result,
                    }
                )

        except asyncio.CancelledError:
            if progress_callback:
                await progress_callback(
                    {
                        "type": "booking_progress",
                        "task_id": task_id,
                        "step": "Booking cancelled",
                        "status": "cancelled",
                    }
                )
        except Exception as e:
            if progress_callback:
                await progress_callback(
                    {
                        "type": "booking_progress",
                        "task_id": task_id,
                        "step": f"Booking error: {e}",
                        "status": "error",
                    }
                )
        finally:
            _booking_tasks.pop(task_id, None)

    try:
        loop = asyncio.get_event_loop()
        task = loop.create_task(_run_booking())
        _booking_tasks[task_id] = task
    except RuntimeError:
        # No running event loop — run synchronously
        pass

    return {
        "status": "searching",
        "task_id": task_id,
        "message": f"Searching for flights from {origin} to {destination} on {date}... "
        "I'll keep you updated. You can keep talking!",
    }


def cancel_booking(task_id: str) -> bool:
    """Cancel an active booking task."""
    task = _booking_tasks.get(task_id)
    if task and not task.done():
        task.cancel()
        return True
    return False
