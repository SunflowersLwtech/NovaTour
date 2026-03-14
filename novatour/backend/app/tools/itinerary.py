"""Itinerary planning tool using Amazon Nova 2 Lite for reasoning."""

import json
import logging

import boto3
from strands import tool

from app.config import settings

logger = logging.getLogger(__name__)

MOCK_ITINERARY = {
    "destination": "Tokyo",
    "days": 5,
    "itinerary": [
        {
            "day": 1,
            "theme": "Arrival & Traditional Tokyo",
            "activities": [
                {"time": "14:00", "activity": "Check in at hotel in Shinjuku", "location": "Shinjuku", "duration": "1h"},
                {"time": "15:30", "activity": "Visit Meiji Jingu Shrine", "location": "Harajuku", "duration": "1.5h"},
                {"time": "18:00", "activity": "Explore Takeshita Street", "location": "Harajuku", "duration": "1h"},
                {"time": "19:30", "activity": "Dinner at Ichiran Ramen", "location": "Shibuya", "duration": "1h"},
            ],
        },
        {
            "day": 2,
            "theme": "Historic East Tokyo",
            "activities": [
                {"time": "09:00", "activity": "Senso-ji Temple & Nakamise Street", "location": "Asakusa", "duration": "2h"},
                {"time": "11:30", "activity": "Tokyo Skytree observation deck", "location": "Sumida", "duration": "1.5h"},
                {"time": "13:30", "activity": "Lunch at Monjayaki restaurant", "location": "Tsukishima", "duration": "1h"},
                {"time": "15:00", "activity": "teamLab Borderless digital art", "location": "Odaiba", "duration": "2h"},
                {"time": "18:00", "activity": "Dinner at local izakaya", "location": "Asakusa", "duration": "1.5h"},
            ],
        },
        {
            "day": 3,
            "theme": "Modern Tokyo & Shopping",
            "activities": [
                {"time": "10:00", "activity": "Tsukiji Outer Market food tour", "location": "Tsukiji", "duration": "2h"},
                {"time": "12:30", "activity": "Ginza shopping district", "location": "Ginza", "duration": "2h"},
                {"time": "15:00", "activity": "Akihabara electronics & anime", "location": "Akihabara", "duration": "2h"},
                {"time": "18:00", "activity": "Dinner at conveyor belt sushi", "location": "Shibuya", "duration": "1h"},
            ],
        },
        {
            "day": 4,
            "theme": "Day Trip to Kamakura",
            "activities": [
                {"time": "08:30", "activity": "Train to Kamakura", "location": "Kamakura", "duration": "1h"},
                {"time": "10:00", "activity": "Great Buddha (Kotoku-in)", "location": "Kamakura", "duration": "1h"},
                {"time": "11:30", "activity": "Hase-dera Temple", "location": "Kamakura", "duration": "1h"},
                {"time": "13:00", "activity": "Lunch at Komachi Street", "location": "Kamakura", "duration": "1h"},
                {"time": "14:30", "activity": "Tsurugaoka Hachimangu Shrine", "location": "Kamakura", "duration": "1.5h"},
                {"time": "17:00", "activity": "Return to Tokyo, evening free", "location": "Shinjuku", "duration": "1h"},
            ],
        },
        {
            "day": 5,
            "theme": "Departure Day",
            "activities": [
                {"time": "09:00", "activity": "Last-minute shopping at Don Quijote", "location": "Shinjuku", "duration": "1.5h"},
                {"time": "11:00", "activity": "Visit Shinjuku Gyoen Garden", "location": "Shinjuku", "duration": "1.5h"},
                {"time": "13:00", "activity": "Final ramen lunch", "location": "Shinjuku", "duration": "1h"},
                {"time": "15:00", "activity": "Head to airport", "location": "NRT/HND", "duration": "1.5h"},
            ],
        },
    ],
    "budget_estimate": {"accommodation": "$900", "food": "$400", "transport": "$200", "activities": "$150", "total": "$1650"},
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
        result = dict(MOCK_ITINERARY)
        result["destination"] = destination
        result["days"] = days
        return result

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

Return a JSON object with this exact structure:
{{
  "destination": "{destination}",
  "days": {days},
  "itinerary": [
    {{
      "day": 1,
      "theme": "Day theme",
      "activities": [
        {{"time": "09:00", "activity": "Description", "location": "Area name", "duration": "1.5h"}}
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

        response = client.converse(
            modelId=settings.nova_lite_model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 4096, "temperature": 0.7},
        )

        text = response["output"]["message"]["content"][0]["text"]

        # Extract JSON from response (may have markdown fencing)
        text = text.strip()
        if text.startswith("```"):
            # Remove markdown code fences
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        return json.loads(text)

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse itinerary JSON: {e}")
        result = dict(MOCK_ITINERARY)
        result["destination"] = destination
        result["days"] = days
        result["fallback_reason"] = f"JSON parse error: {e}"
        return result
    except Exception as e:
        logger.warning(f"Itinerary planning failed: {e}, returning mock data")
        result = dict(MOCK_ITINERARY)
        result["destination"] = destination
        result["days"] = days
        result["fallback_reason"] = str(e)
        result["mock"] = True
        return result
