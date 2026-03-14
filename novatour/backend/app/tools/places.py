"""Place search tool using Google Places API (New)."""

import logging
import math

import httpx
from strands import tool

from app.config import settings
from app.utils.resilience import retry_api_call, timed_log

logger = logging.getLogger(__name__)

_PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
_FIELD_MASK = (
    "places.displayName,"
    "places.formattedAddress,"
    "places.types,"
    "places.rating,"
    "places.userRatingCount,"
    "places.location,"
    "places.currentOpeningHours,"
    "places.websiteUri,"
    "places.photos"
)

# Google Places API photo URL template
_PHOTO_URL_TEMPLATE = "https://places.googleapis.com/v1/{photo_name}/media?maxWidthPx=640&key={api_key}"

def _mock_places(query: str) -> dict:
    return {
        "places": [
            {"name": f"Popular Attraction 1 ({query})", "address": f"Central area", "lat": 0, "lon": 0, "rating": 4.5, "types": ["tourist_attraction"]},
            {"name": f"Popular Attraction 2 ({query})", "address": f"Historic district", "lat": 0, "lon": 0, "rating": 4.7, "types": ["tourist_attraction"]},
            {"name": f"Popular Attraction 3 ({query})", "address": f"Waterfront area", "lat": 0, "lon": 0, "rating": 4.4, "types": ["tourist_attraction"]},
        ],
        "count": 3, "query": query, "mock": True,
    }


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in meters."""
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@tool
def search_places(
    query: str,
    latitude: float = 0.0,
    longitude: float = 0.0,
    radius: int = 5000,
    limit: int = 10,
) -> dict:
    """Search for attractions, restaurants, and places of interest.

    Args:
        query: What to find (e.g. 'ramen restaurants in Tokyo')
        latitude: Latitude for proximity search (0 to skip)
        longitude: Longitude for proximity search (0 to skip)
        radius: Search radius in meters
        limit: Max results to return
    """
    if settings.mock_mode:
        return _mock_places(query)

    try:
        api_key = settings.google_maps_api_key
        if not api_key:
            return {**_mock_places(query), "fallback_reason": "GOOGLE_MAPS_API_KEY not configured"}

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
        }

        has_coords = latitude != 0.0 and longitude != 0.0

        # Use Text Search (works with or without coordinates)
        body = {
            "textQuery": query,
            "maxResultCount": limit,
        }
        if has_coords:
            body["locationBias"] = {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": float(radius),
                }
            }

        @retry_api_call()
        def _call_api():
            with httpx.Client(timeout=settings.tool_timeout) as client:
                resp = client.post(_PLACES_TEXT_SEARCH_URL, json=body, headers=headers)
                resp.raise_for_status()
                return resp.json()

        with timed_log(logger, "search_places"):
            data = _call_api()

        places = []
        for place in data.get("places", [])[:limit]:
            display_name = place.get("displayName", {})
            location = place.get("location", {})
            lat = location.get("latitude", 0)
            lon = location.get("longitude", 0)

            # Extract first photo URL if available
            photo_url = ""
            photos = place.get("photos", [])
            if photos and api_key:
                photo_name = photos[0].get("name", "")
                if photo_name:
                    photo_url = _PHOTO_URL_TEMPLATE.format(
                        photo_name=photo_name, api_key=api_key
                    )

            place_info = {
                "name": display_name.get("text", "Unknown"),
                "address": place.get("formattedAddress", ""),
                "lat": lat,
                "lon": lon,
                "rating": place.get("rating", 0),
                "review_count": place.get("userRatingCount", 0),
                "types": place.get("types", [])[:3],
                "website": place.get("websiteUri", ""),
                "photo_url": photo_url,
            }

            if has_coords:
                place_info["distance_m"] = round(_haversine_m(latitude, longitude, lat, lon))

            places.append(place_info)

        if has_coords:
            places.sort(key=lambda p: p.get("distance_m", 0))

        return {"places": places, "count": len(places), "query": query}

    except Exception as e:
        logger.warning(f"Place search failed: {e}, returning mock data")
        return {**_mock_places(query), "fallback_reason": str(e)}
