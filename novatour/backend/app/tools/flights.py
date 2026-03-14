"""Flight search tool using Google Gemini Search grounding."""

import logging

from strands import tool

from app.config import settings

logger = logging.getLogger(__name__)

MOCK_FLIGHTS = {
    "flights": [
        {
            "price": "~450 USD",
            "airline": "ANA",
            "route": "NRT → CDG",
            "duration": "~12h 30m",
            "stops": "Direct",
        },
        {
            "price": "~520 USD",
            "airline": "Air France",
            "route": "NRT → CDG",
            "duration": "~12h 45m",
            "stops": "Direct",
        },
        {
            "price": "~380 USD",
            "airline": "Cathay Pacific",
            "route": "NRT → HKG → CDG",
            "duration": "~16h 20m",
            "stops": "1 stop",
        },
    ],
    "count": 3,
    "mock": True,
}


@tool
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str = "",
    adults: int = 1,
) -> dict:
    """Search flights between cities. Returns prices, airlines, schedules.

    Args:
        origin: Departure city or airport
        destination: Arrival city or airport
        departure_date: YYYY-MM-DD format
        return_date: Return date for round-trip (optional)
        adults: Number of passengers
    """
    if settings.mock_mode:
        return MOCK_FLIGHTS

    try:
        from google import genai
        from google.genai import types

        api_key = settings.google_api_key
        if not api_key:
            return {**MOCK_FLIGHTS, "fallback_reason": "GOOGLE_API_KEY not configured"}

        client = genai.Client(api_key=api_key)

        trip_type = "round-trip" if return_date else "one-way"
        query = (
            f"Find {trip_type} flights from {origin} to {destination} "
            f"departing {departure_date}"
        )
        if return_date:
            query += f" returning {return_date}"
        query += f" for {adults} adult(s). Show prices, airlines, duration, and number of stops."

        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-05-20",
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1,
            ),
        )

        answer = response.text or "No flight information found."

        sources = []
        if response.candidates and response.candidates[0].grounding_metadata:
            gm = response.candidates[0].grounding_metadata
            for chunk in getattr(gm, "grounding_chunks", []) or []:
                web = getattr(chunk, "web", None)
                if web:
                    sources.append({"title": web.title or "", "url": web.uri or ""})

        return {
            "summary": answer,
            "sources": sources[:5],
            "query": query,
        }

    except Exception as e:
        logger.warning(f"Flight search failed: {e}, returning mock data")
        return {**MOCK_FLIGHTS, "fallback_reason": str(e)}
