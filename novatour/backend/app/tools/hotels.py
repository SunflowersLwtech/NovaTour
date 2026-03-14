"""Hotel search tool using Google Places API (New)."""

import logging

import httpx
from strands import tool

from app.config import settings

logger = logging.getLogger(__name__)

_PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_FIELD_MASK = (
    "places.displayName,"
    "places.formattedAddress,"
    "places.rating,"
    "places.userRatingCount,"
    "places.location,"
    "places.priceLevel,"
    "places.websiteUri,"
    "places.types"
)

MOCK_HOTELS = {
    "hotels": [
        {
            "name": "Grand Tokyo Hotel",
            "rating": 4.2,
            "address": "1-2-3 Shinjuku, Tokyo",
            "price_level": "MODERATE",
        },
        {
            "name": "Sakura Inn",
            "rating": 3.8,
            "address": "4-5-6 Shibuya, Tokyo",
            "price_level": "INEXPENSIVE",
        },
        {
            "name": "Imperial Palace Hotel",
            "rating": 4.7,
            "address": "7-8-9 Chiyoda, Tokyo",
            "price_level": "EXPENSIVE",
        },
    ],
    "count": 3,
    "mock": True,
}


@tool
def search_hotels(
    city: str,
    check_in: str = "",
    check_out: str = "",
    max_results: int = 5,
) -> dict:
    """Search hotels in a city. Returns names, ratings, addresses, prices.

    Args:
        city: City name to search
        check_in: Check-in date YYYY-MM-DD (optional)
        check_out: Check-out date YYYY-MM-DD (optional)
        max_results: Max results to return
    """
    if settings.mock_mode:
        return MOCK_HOTELS

    try:
        api_key = settings.google_maps_api_key
        if not api_key:
            return {**MOCK_HOTELS, "fallback_reason": "GOOGLE_MAPS_API_KEY not configured"}

        text_query = f"hotels in {city}"
        if check_in:
            text_query += f" for {check_in}"

        body = {
            "textQuery": text_query,
            "maxResultCount": max_results,
            "includedType": "hotel",
        }

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
        }

        with httpx.Client(timeout=10) as client:
            resp = client.post(_PLACES_TEXT_SEARCH_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        hotels = []
        for place in data.get("places", [])[:max_results]:
            display_name = place.get("displayName", {})
            location = place.get("location", {})
            hotels.append({
                "name": display_name.get("text", "Unknown Hotel"),
                "rating": place.get("rating", 0),
                "review_count": place.get("userRatingCount", 0),
                "address": place.get("formattedAddress", ""),
                "price_level": place.get("priceLevel", "N/A"),
                "website": place.get("websiteUri", ""),
                "lat": location.get("latitude", 0),
                "lon": location.get("longitude", 0),
            })

        return {"hotels": hotels, "count": len(hotels), "city": city}

    except Exception as e:
        logger.warning(f"Hotel search failed: {e}, returning mock data")
        return {**MOCK_HOTELS, "fallback_reason": str(e)}
