"""API integration tests for NovaTour travel tools.

Tests each tool directly with real API calls (bypass voice pipeline).
Run with: cd novatour/backend && MOCK_MODE=false conda run -n novatour python -m pytest tests/test_api_integrations.py -v
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


@pytest.fixture(autouse=True)
def live_mode(monkeypatch):
    """Disable mock mode for all tests in this file."""
    monkeypatch.setenv("MOCK_MODE", "false")
    from app.config import Settings

    live = Settings()
    monkeypatch.setattr("app.tools.weather.settings", live)
    monkeypatch.setattr("app.tools.places.settings", live)
    monkeypatch.setattr("app.tools.hotels.settings", live)
    monkeypatch.setattr("app.tools.routes.settings", live)
    monkeypatch.setattr("app.tools.flights.settings", live)
    monkeypatch.setattr("app.tools.itinerary.settings", live)
    return live


@pytest.mark.skipif(
    os.getenv("MOCK_MODE", "true").lower() != "false",
    reason="API integration tests only run with MOCK_MODE=false",
)
class TestAPIIntegrations:
    """Direct API integration tests for each tool."""

    def test_get_weather(self):
        from app.tools.weather import get_weather

        result = get_weather("Tokyo")
        assert "temperature" in result
        assert "mock" not in result, "Got mock data instead of live API response"

    def test_get_forecast(self):
        from app.tools.weather import get_forecast

        result = get_forecast("Tokyo", days=2)
        assert "days" in result
        assert isinstance(result["days"], list)
        assert len(result["days"]) > 0

    def test_search_hotels(self):
        from app.tools.hotels import search_hotels

        result = search_hotels("Tokyo", max_results=2)
        assert "hotels" in result
        assert len(result["hotels"]) > 0
        hotel = result["hotels"][0]
        assert "name" in hotel
        assert "rating" in hotel

    def test_search_places(self):
        from app.tools.places import search_places

        result = search_places("Tokyo Tower")
        assert "places" in result
        assert len(result["places"]) > 0
        place = result["places"][0]
        assert "lat" in place
        assert "lon" in place

    def test_plan_route(self):
        from app.tools.routes import plan_route

        result = plan_route("Tokyo Station", "Shinjuku Station")
        assert "distance_km" in result
        assert result["distance_km"] > 0

    def test_search_flights(self):
        from app.tools.flights import search_flights

        result = search_flights("Tokyo", "Paris", "2026-05-01")
        # Live returns "summary" key, mock returns "flights" key
        assert "summary" in result or "flights" in result

    def test_plan_itinerary(self):
        from app.tools.itinerary import plan_itinerary

        result = plan_itinerary("Tokyo", days=2)
        assert "itinerary" in result
        assert isinstance(result["itinerary"], list)
