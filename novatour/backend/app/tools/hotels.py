"""Hotel search tool using Google Places API (New)."""

import logging

import httpx
from strands import tool

from app.config import settings
from app.utils.resilience import retry_api_call, timed_log

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
    "places.types,"
    "places.photos"
)

_PHOTO_URL_TEMPLATE = "https://places.googleapis.com/v1/{photo_name}/media?maxWidthPx=640&key={api_key}"

def _mock_hotels(city: str) -> dict:
    return {
        "hotels": [
            {"name": f"Grand {city} Hotel", "rating": 4.2, "address": f"Central {city}", "price_level": "MODERATE"},
            {"name": f"{city} Budget Inn", "rating": 3.8, "address": f"Downtown {city}", "price_level": "INEXPENSIVE"},
            {"name": f"Premium {city} Suites", "rating": 4.7, "address": f"Uptown {city}", "price_level": "EXPENSIVE"},
        ],
        "count": 3, "city": city, "mock": True,
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
        return _mock_hotels(city)

    try:
        api_key = settings.google_maps_api_key
        if not api_key:
            return {**_mock_hotels(city), "fallback_reason": "GOOGLE_MAPS_API_KEY not configured"}

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

        @retry_api_call()
        def _call_api():
            with httpx.Client(timeout=settings.tool_timeout) as client:
                resp = client.post(_PLACES_TEXT_SEARCH_URL, json=body, headers=headers)
                resp.raise_for_status()
                return resp.json()

        with timed_log(logger, "search_hotels"):
            data = _call_api()

        hotels = []
        for place in data.get("places", [])[:max_results]:
            display_name = place.get("displayName", {})
            location = place.get("location", {})
            photo_url = ""
            photos = place.get("photos", [])
            if photos and api_key:
                photo_name = photos[0].get("name", "")
                if photo_name:
                    photo_url = _PHOTO_URL_TEMPLATE.format(
                        photo_name=photo_name, api_key=api_key
                    )

            hotels.append({
                "name": display_name.get("text", "Unknown Hotel"),
                "rating": place.get("rating", 0),
                "review_count": place.get("userRatingCount", 0),
                "address": place.get("formattedAddress", ""),
                "price_level": place.get("priceLevel", "N/A"),
                "website": place.get("websiteUri", ""),
                "lat": location.get("latitude", 0),
                "lon": location.get("longitude", 0),
                "photo_url": photo_url,
            })

        return {"hotels": hotels, "count": len(hotels), "city": city}

    except Exception as e:
        logger.warning(f"Hotel search failed: {e}, returning mock data")
        return {**_mock_hotels(city), "fallback_reason": str(e)}
