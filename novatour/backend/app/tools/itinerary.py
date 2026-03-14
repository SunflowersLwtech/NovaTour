"""Itinerary planning tool using Amazon Nova 2 Lite for reasoning."""

import logging

import boto3
from strands import tool

from app.config import settings
from app.utils.resilience import retry_api_call, safe_json_loads, timed_log

logger = logging.getLogger(__name__)

def _mock_itinerary(destination: str, days: int) -> dict:
    """Generate a generic mock itinerary based on user parameters."""
    themes = [
        "Arrival & First Impressions", "History & Culture", "Local Food & Markets",
        "Nature & Outdoors", "Art & Architecture", "Shopping & Entertainment",
        "Day Trip to Nearby Attraction", "Departure Day",
    ]
    day_plans = []
    for i in range(min(days, len(themes))):
        activities = [
            {"time": "09:00", "activity": f"Morning exploration in {destination}", "location": f"Central {destination}", "duration": "2h"},
            {"time": "11:30", "activity": f"Visit a top-rated attraction", "location": f"{destination}", "duration": "1.5h"},
            {"time": "13:00", "activity": f"Lunch at a local restaurant", "location": f"{destination}", "duration": "1h"},
            {"time": "14:30", "activity": f"Afternoon activity — {themes[i].lower()}", "location": f"{destination}", "duration": "2h"},
        ]
        if i == 0:
            activities[0] = {"time": "14:00", "activity": f"Check in at hotel in {destination}", "location": f"Central {destination}", "duration": "1h"}
        if i == days - 1:
            activities.append({"time": "17:00", "activity": "Head to airport", "location": f"{destination} Airport", "duration": "1.5h"})
        day_plans.append({"day": i + 1, "theme": themes[i], "activities": activities})

    per_day = 350
    return {
        "destination": destination, "days": days, "itinerary": day_plans,
        "budget_estimate": {
            "accommodation": f"${days * 150}", "food": f"${days * 60}",
            "transport": f"${days * 30}", "activities": f"${days * 25}",
            "total": f"${days * per_day}",
        },
        "mock": True,
    }


@tool
def plan_itinerary(
    destination: str,
    days: int = 3,
    budget: str = "",
    interests: str = "",
    travelers: int = 1,
) -> dict:
    """Create a day-by-day travel itinerary with activities and budget.

    Args:
        destination: City or region to plan for
        days: Number of days (default 3)
        budget: Budget level or amount (optional)
        interests: Comma-separated interests (optional)
        travelers: Number of travelers
    """
    if settings.mock_mode:
        return _mock_itinerary(destination, days)

    try:
        client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_default_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

        budget_text = f" with a budget of {budget}" if budget else ""
        interests_text = f" who enjoys {interests}" if interests else ""
        travelers_text = f" for {travelers} travelers" if travelers > 1 else ""

        prompt = f"""Create a detailed {days}-day travel itinerary for {destination}{budget_text}{travelers_text}{interests_text}.

Include approximate latitude and longitude coordinates for each activity location.

Return a JSON object with this exact structure:
{{
  "destination": "{destination}",
  "days": {days},
  "itinerary": [
    {{
      "day": 1,
      "theme": "Day theme",
      "activities": [
        {{"time": "09:00", "activity": "Description", "location": "Area name", "duration": "1.5h", "latitude": 35.6762, "longitude": 139.6503}}
      ]
    }}
  ],
  "budget_estimate": {{
    "accommodation": "$X",
    "food": "$X",
    "transport": "$X",
    "activities": "$X",
    "total": "$X"
  }},
  "tips": ["tip1", "tip2"]
}}

Return ONLY the JSON, no other text."""

        @retry_api_call(retry_on=(Exception,))
        def _call_api():
            return client.converse(
                modelId=settings.nova_lite_model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 4096, "temperature": 0.7},
            )

        with timed_log(logger, "plan_itinerary"):
            response = _call_api()

        text = response["output"]["message"]["content"][0]["text"]
        parsed = safe_json_loads(text)
        if parsed is not None:
            return parsed

        # safe_json_loads returned None — treat as parse failure
        logger.warning("Failed to parse itinerary JSON")
        result = _mock_itinerary(destination, days)
        result["fallback_reason"] = "JSON parse error: could not parse model response"
        return result
    except Exception as e:
        logger.warning(f"Itinerary planning failed: {e}, returning mock data")
        result = _mock_itinerary(destination, days)
        result["fallback_reason"] = str(e)
        result["mock"] = True
        return result
