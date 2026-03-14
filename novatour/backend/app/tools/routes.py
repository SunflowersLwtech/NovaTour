"""Route planning tool using Google Routes API v2."""

import logging

import httpx
from strands import tool

from app.config import settings
from app.utils.resilience import retry_api_call, timed_log

logger = logging.getLogger(__name__)

_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

_MODE_MAP = {
    "drive": "DRIVE",
    "walk": "WALK",
    "bicycle": "BICYCLE",
    "transit": "TRANSIT",
}

MOCK_ROUTE = {
    "distance_km": 12.5,
    "duration_min": 25.3,
    "mode": "drive",
    "steps": [
        {"instruction": "Head north on Main Street", "distance_km": 0.5},
        {"instruction": "Turn right onto Highway 1", "distance_km": 10.0},
        {"instruction": "Take exit toward Downtown", "distance_km": 2.0},
    ],
    "mock": True,
}


@tool
def plan_route(
    origin: str,
    destination: str,
    mode: str = "drive",
) -> dict:
    """Get directions between two locations with distance and duration.

    Args:
        origin: Starting location (address or place name)
        destination: Destination (address or place name)
        mode: 'drive', 'walk', 'bicycle', or 'transit'
    """
    if settings.mock_mode:
        return MOCK_ROUTE

    try:
        api_key = settings.google_maps_api_key
        if not api_key:
            return {**MOCK_ROUTE, "fallback_reason": "GOOGLE_MAPS_API_KEY not configured"}

        travel_mode = _MODE_MAP.get(mode, "DRIVE")

        body = {
            "origin": {"address": origin},
            "destination": {"address": destination},
            "travelMode": travel_mode,
            "languageCode": "en",
            "units": "METRIC",
        }

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline,routes.legs.steps.navigationInstruction,routes.legs.steps.distanceMeters",
        }

        @retry_api_call()
        def _call_api():
            with httpx.Client(timeout=settings.tool_timeout) as client:
                resp = client.post(_ROUTES_URL, json=body, headers=headers)
                resp.raise_for_status()
                return resp.json()

        with timed_log(logger, "plan_route"):
            data = _call_api()

        routes = data.get("routes", [])
        if not routes:
            return {"error": "No route found between the given locations"}

        route = routes[0]
        distance_m = route.get("distanceMeters", 0)
        duration_str = route.get("duration", "0s")
        duration_s = int(duration_str.rstrip("s")) if duration_str.endswith("s") else 0

        steps = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                nav = step.get("navigationInstruction", {})
                instruction = nav.get("instructions", "Continue")
                step_distance = step.get("distanceMeters", 0)
                steps.append({
                    "instruction": instruction,
                    "distance_km": round(step_distance / 1000, 2),
                })

        return {
            "distance_km": round(distance_m / 1000, 2),
            "duration_min": round(duration_s / 60, 1),
            "mode": mode,
            "origin": origin,
            "destination": destination,
            "steps": steps[:15],
        }

    except Exception as e:
        logger.warning(f"Route planning failed: {e}, returning mock data")
        return {**MOCK_ROUTE, "fallback_reason": str(e)}
