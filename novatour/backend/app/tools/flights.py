"""Flight search tool using Google Gemini Search grounding."""

import logging

from strands import tool

from app.config import settings
from app.utils.resilience import retry_api_call, timed_log

logger = logging.getLogger(__name__)

def _mock_flights(origin: str, destination: str) -> dict:
    """Generate mock flight data that reflects the user's query."""
    return {
        "summary": (
            f"Here are sample flight options from {origin} to {destination}:\n"
            f"1. Major carrier direct flight: ~$450-600, approximately 8-14 hours\n"
            f"2. Budget option with 1 stop: ~$300-450, approximately 12-18 hours\n"
            f"3. Premium direct flight: ~$600-900, approximately 8-14 hours\n"
            f"(Mock data — connect a Google API key for real-time results)"
        ),
        "sources": [],
        "query": f"flights from {origin} to {destination}",
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
        return _mock_flights(origin, destination)

    try:
        from google import genai
        from google.genai import types

        api_key = settings.google_api_key
        if not api_key:
            return {**_mock_flights(origin, destination), "fallback_reason": "GOOGLE_API_KEY not configured"}

        client = genai.Client(api_key=api_key)

        trip_type = "round-trip" if return_date else "one-way"
        query = (
            f"Find {trip_type} flights from {origin} to {destination} "
            f"departing {departure_date}"
        )
        if return_date:
            query += f" returning {return_date}"
        query += f" for {adults} adult(s). Show prices, airlines, duration, and number of stops."

        @retry_api_call(retry_on=(Exception,))
        def _call_api():
            return client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.1,
                ),
            )

        with timed_log(logger, "search_flights"):
            response = _call_api()

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
        return {**_mock_flights(origin, destination), "fallback_reason": str(e)}
