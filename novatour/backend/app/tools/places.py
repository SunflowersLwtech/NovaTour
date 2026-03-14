"""Place search tool using Google Places API (New)."""

import logging
import math

import httpx
from strands import tool

from app.config import settings

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
    "places.websiteUri"
)

MOCK_PLACES = {
    "places": [
        {
            "name": "Senso-ji Temple",
            "address": "2 Chome-3-1 Asakusa, Taito City, Tokyo",
            "lat": 35.7148,
            "lon": 139.7967,
            "rating": 4.5,
            "types": ["tourist_attraction", "place_of_worship"],
        },
        {
            "name": "Meiji Jingu Shrine",
            "address": "1-1 Yoyogikamizonocho, Shibuya City, Tokyo",
            "lat": 35.6764,
            "lon": 139.6993,
            "rating": 4.7,
            "types": ["tourist_attraction", "place_of_worship"],
        },
        {
            "name": "Tokyo Skytree",
            "address": "1 Chome-1-2 Oshiage, Sumida City, Tokyo",
            "lat": 35.7101,
            "lon": 139.8107,
            "rating": 4.4,
            "types": ["tourist_attraction"],
        },
    ],
    "count": 3,
    "mock": True,
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
        return MOCK_PLACES

    try:
        api_key = settings.google_maps_api_key
        if not api_key:
            return {**MOCK_PLACES, "fallback_reason": "GOOGLE_MAPS_API_KEY not configured"}

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

        with httpx.Client(timeout=10) as client:
            resp = client.post(_PLACES_TEXT_SEARCH_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        places = []
        for place in data.get("places", [])[:limit]:
            display_name = place.get("displayName", {})
            location = place.get("location", {})
            lat = location.get("latitude", 0)
            lon = location.get("longitude", 0)

            place_info = {
                "name": display_name.get("text", "Unknown"),
                "address": place.get("formattedAddress", ""),
                "lat": lat,
                "lon": lon,
                "rating": place.get("rating", 0),
                "review_count": place.get("userRatingCount", 0),
                "types": place.get("types", [])[:3],
                "website": place.get("websiteUri", ""),
            }

            if has_coords:
                place_info["distance_m"] = round(_haversine_m(latitude, longitude, lat, lon))

            places.append(place_info)

        if has_coords:
            places.sort(key=lambda p: p.get("distance_m", 0))

        return {"places": places, "count": len(places), "query": query}

    except Exception as e:
        logger.warning(f"Place search failed: {e}, returning mock data")
        return {**MOCK_PLACES, "fallback_reason": str(e)}
