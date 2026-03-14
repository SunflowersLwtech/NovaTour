"""Weather tools using OpenWeather API."""

import logging

import httpx
from strands import tool

from app.config import settings

logger = logging.getLogger(__name__)

OWM_BASE = "https://api.openweathermap.org/data/2.5"

MOCK_WEATHER = {
    "city": "Tokyo",
    "country": "JP",
    "temperature": 22.0,
    "feels_like": 21.5,
    "description": "clear sky",
    "humidity": 55,
    "wind_speed": 3.5,
    "pressure": 1013,
    "mock": True,
}

MOCK_FORECAST = {
    "city": "Tokyo",
    "country": "JP",
    "days": [
        {"date": "2026-04-01", "temp_min": 18.0, "temp_max": 24.0, "description": "clear sky", "humidity": 50},
        {"date": "2026-04-02", "temp_min": 17.0, "temp_max": 23.0, "description": "few clouds", "humidity": 55},
        {"date": "2026-04-03", "temp_min": 15.0, "temp_max": 20.0, "description": "light rain", "humidity": 70},
        {"date": "2026-04-04", "temp_min": 16.0, "temp_max": 22.0, "description": "scattered clouds", "humidity": 60},
        {"date": "2026-04-05", "temp_min": 19.0, "temp_max": 25.0, "description": "clear sky", "humidity": 45},
    ],
    "mock": True,
}


@tool
def get_weather(
    city: str,
    latitude: float = 0.0,
    longitude: float = 0.0,
) -> dict:
    """Get current weather for a city. Returns temperature, humidity, conditions.

    Args:
        city: City name (used if no coordinates)
        latitude: Latitude (0 to use city name)
        longitude: Longitude (0 to use city name)
    """
    if settings.mock_mode:
        return {**MOCK_WEATHER, "city": city}

    try:
        api_key = settings.openweather_api_key
        if not api_key:
            return {**MOCK_WEATHER, "city": city, "fallback_reason": "OpenWeather API key not configured"}

        params = {
            "appid": api_key,
            "units": "metric",
        }
        if latitude != 0.0 and longitude != 0.0:
            params["lat"] = latitude
            params["lon"] = longitude
        else:
            params["q"] = city

        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{OWM_BASE}/weather", params=params)
            resp.raise_for_status()
            data = resp.json()

        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        wind = data.get("wind", {})

        return {
            "city": data.get("name", city),
            "country": data.get("sys", {}).get("country", ""),
            "temperature": main.get("temp", 0),
            "feels_like": main.get("feels_like", 0),
            "temp_min": main.get("temp_min", 0),
            "temp_max": main.get("temp_max", 0),
            "description": weather.get("description", ""),
            "humidity": main.get("humidity", 0),
            "wind_speed": wind.get("speed", 0),
            "wind_direction": wind.get("deg", 0),
            "pressure": main.get("pressure", 0),
            "visibility_km": round(data.get("visibility", 0) / 1000, 1),
            "clouds": data.get("clouds", {}).get("all", 0),
        }

    except Exception as e:
        logger.warning(f"Weather fetch failed: {e}, returning mock data")
        return {**MOCK_WEATHER, "city": city, "fallback_reason": str(e)}


@tool
def get_forecast(
    city: str,
    days: int = 5,
    latitude: float = 0.0,
    longitude: float = 0.0,
) -> dict:
    """Get multi-day weather forecast. Returns daily temps and conditions.

    Args:
        city: City name (used if no coordinates)
        days: Number of days (1-5)
        latitude: Latitude (0 to use city name)
        longitude: Longitude (0 to use city name)
    """
    if settings.mock_mode:
        return {**MOCK_FORECAST, "city": city}

    try:
        api_key = settings.openweather_api_key
        if not api_key:
            return {**MOCK_FORECAST, "city": city, "fallback_reason": "OpenWeather API key not configured"}

        days = min(max(days, 1), 5)
        params = {
            "appid": api_key,
            "units": "metric",
            "cnt": days * 8,  # 8 forecasts per day (3-hour intervals)
        }
        if latitude != 0.0 and longitude != 0.0:
            params["lat"] = latitude
            params["lon"] = longitude
        else:
            params["q"] = city

        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{OWM_BASE}/forecast", params=params)
            resp.raise_for_status()
            data = resp.json()

        city_info = data.get("city", {})
        forecasts = data.get("list", [])

        # Group by date
        daily: dict[str, list] = {}
        for fc in forecasts:
            date = fc["dt_txt"].split(" ")[0]
            daily.setdefault(date, []).append(fc)

        result_days = []
        for date, entries in list(daily.items())[:days]:
            temps = [e["main"]["temp"] for e in entries]
            # Pick midday entry for description
            mid = entries[len(entries) // 2]
            result_days.append(
                {
                    "date": date,
                    "temp_min": round(min(temps), 1),
                    "temp_max": round(max(temps), 1),
                    "description": mid["weather"][0]["description"],
                    "humidity": mid["main"]["humidity"],
                    "wind_speed": mid["wind"]["speed"],
                }
            )

        return {
            "city": city_info.get("name", city),
            "country": city_info.get("country", ""),
            "days": result_days,
        }

    except Exception as e:
        logger.warning(f"Forecast fetch failed: {e}, returning mock data")
        return {**MOCK_FORECAST, "city": city, "fallback_reason": str(e)}
