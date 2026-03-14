"""Tests for NovaTour travel tools.

Run with: cd novatour/backend && conda run -n novatour python -m pytest tests/test_tools.py -v
Live API: MOCK_MODE=false conda run -n novatour python -m pytest tests/test_tools.py -v
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def enable_mock_mode(monkeypatch):
    """Enable mock mode for all tests by default."""
    monkeypatch.setenv("MOCK_MODE", "true")
    from app.config import Settings

    mock_settings = Settings()
    monkeypatch.setattr("app.tools.flights.settings", mock_settings)
    monkeypatch.setattr("app.tools.hotels.settings", mock_settings)
    monkeypatch.setattr("app.tools.places.settings", mock_settings)
    monkeypatch.setattr("app.tools.routes.settings", mock_settings)
    monkeypatch.setattr("app.tools.weather.settings", mock_settings)
    monkeypatch.setattr("app.tools.itinerary.settings", mock_settings)
    monkeypatch.setattr("app.tools.booking.settings", mock_settings)


# ── Import Tests ──────────────────────────────────────────────


def test_all_tools_importable():
    """ALL_TOOLS list can be imported and contains 8 tools."""
    from app.tools import ALL_TOOLS

    assert len(ALL_TOOLS) == 8


def test_tool_names():
    """Each tool has a proper name."""
    from app.tools import ALL_TOOLS

    names = [t.tool_name for t in ALL_TOOLS]
    expected = [
        "search_flights",
        "search_hotels",
        "search_places",
        "plan_route",
        "get_weather",
        "get_forecast",
        "plan_itinerary",
        "book_flight",
    ]
    for name in expected:
        assert name in names, f"Missing tool: {name}"


def test_tool_specs():
    """Each tool has a valid tool_spec with description."""
    from app.tools import ALL_TOOLS

    for t in ALL_TOOLS:
        spec = t.tool_spec
        assert spec.get("name"), f"Tool missing name: {t}"
        assert spec.get("description"), f"Tool {spec.get('name')} missing description"


# ── Flight Tool Tests ─────────────────────────────────────────


def test_search_flights_mock():
    from app.tools.flights import search_flights

    result = search_flights("London", "Rome", "2026-06-01")
    assert "summary" in result or "flights" in result
    assert result.get("mock") is True


def test_search_flights_mock_reflects_query():
    from app.tools.flights import search_flights

    result = search_flights("London", "Rome", "2026-06-01")
    summary = result.get("summary", "") + result.get("query", "")
    assert "London" in summary or "london" in summary.lower()
    assert "Rome" in summary or "rome" in summary.lower()


# ── Hotel Tool Tests ──────────────────────────────────────────


def test_search_hotels_mock():
    from app.tools.hotels import search_hotels

    result = search_hotels("Tokyo")
    assert "hotels" in result
    assert isinstance(result["hotels"], list)
    assert len(result["hotels"]) > 0
    assert result.get("mock") is True


def test_search_hotels_mock_fields():
    from app.tools.hotels import search_hotels

    result = search_hotels("Tokyo")
    hotel = result["hotels"][0]
    assert "name" in hotel
    assert "rating" in hotel
    assert "address" in hotel


# ── Places Tool Tests ─────────────────────────────────────────


def test_search_places_mock():
    from app.tools.places import search_places

    result = search_places("ramen restaurants in Tokyo")
    assert "places" in result
    assert isinstance(result["places"], list)
    assert len(result["places"]) > 0
    assert result.get("mock") is True


def test_search_places_mock_fields():
    from app.tools.places import search_places

    result = search_places("temples in Kyoto")
    place = result["places"][0]
    assert "name" in place
    assert "lat" in place
    assert "lon" in place


# ── Route Tool Tests ──────────────────────────────────────────


def test_plan_route_mock():
    from app.tools.routes import plan_route

    result = plan_route("Tokyo Station", "Senso-ji Temple")
    assert "distance_km" in result
    assert "duration_min" in result
    assert "mode" in result
    assert result.get("mock") is True


def test_plan_route_mock_steps():
    from app.tools.routes import plan_route

    result = plan_route("Shinjuku", "Shibuya", mode="walk")
    assert "steps" in result
    assert isinstance(result["steps"], list)


# ── Weather Tool Tests ────────────────────────────────────────


def test_get_weather_mock():
    from app.tools.weather import get_weather

    result = get_weather("Tokyo")
    assert "temperature" in result
    assert "city" in result
    assert result["city"] == "Tokyo"
    assert result.get("mock") is True


def test_get_forecast_mock():
    from app.tools.weather import get_forecast

    result = get_forecast("Tokyo", days=3)
    assert "days" in result
    assert isinstance(result["days"], list)
    assert result.get("mock") is True


# ── Itinerary Tool Tests ─────────────────────────────────────


def test_plan_itinerary_mock():
    from app.tools.itinerary import plan_itinerary

    result = plan_itinerary("Tokyo", days=5, interests="ramen, temples")
    assert "itinerary" in result
    assert isinstance(result["itinerary"], list)
    assert result["destination"] == "Tokyo"
    assert result.get("mock") is True


# ── Booking Tool Tests ────────────────────────────────────────


def test_book_flight_mock():
    from app.tools.booking import book_flight

    result = book_flight("Tokyo", "Paris", "April 1 2026")
    assert "status" in result
    assert result["status"] == "found"
    assert "booking" in result
    assert result.get("mock") is True


# ── Live API Tests (skipped unless MOCK_MODE=false) ───────────


@pytest.fixture
def live_settings(monkeypatch):
    """Disable mock mode for live API tests."""
    monkeypatch.setenv("MOCK_MODE", "false")
    from app.config import Settings

    settings = Settings()
    monkeypatch.setattr("app.tools.weather.settings", settings)
    monkeypatch.setattr("app.tools.places.settings", settings)
    monkeypatch.setattr("app.tools.hotels.settings", settings)
    monkeypatch.setattr("app.tools.routes.settings", settings)
    monkeypatch.setattr("app.tools.flights.settings", settings)
    return settings


@pytest.mark.skipif(
    os.getenv("MOCK_MODE", "true").lower() != "false",
    reason="Live API tests only run with MOCK_MODE=false",
)
class TestLiveAPIs:
    """Tests that hit real APIs. Run with MOCK_MODE=false."""

    def test_live_weather(self, live_settings):
        from app.tools.weather import get_weather

        result = get_weather("Tokyo")
        assert "temperature" in result or "error" in result
        assert result.get("mock") is not True

    def test_live_forecast(self, live_settings):
        from app.tools.weather import get_forecast

        result = get_forecast("Paris", days=3)
        assert "days" in result or "error" in result

    def test_live_places(self, live_settings):
        from app.tools.places import search_places

        result = search_places("Tokyo Tower")
        assert "places" in result
        assert result["count"] > 0
        assert result.get("mock") is not True

    def test_live_hotels(self, live_settings):
        from app.tools.hotels import search_hotels

        result = search_hotels("Kyoto", max_results=3)
        assert "hotels" in result
        assert result["count"] > 0
        assert result.get("mock") is not True

    def test_live_route(self, live_settings):
        from app.tools.routes import plan_route

        result = plan_route("Tokyo Station", "Shinjuku Station")
        assert "distance_km" in result
        assert result["distance_km"] > 0
        assert result.get("mock") is not True

    def test_live_places_with_coords(self, live_settings):
        from app.tools.places import search_places

        # Near Tokyo Station
        result = search_places(
            "coffee shop", latitude=35.6812, longitude=139.7671, radius=500
        )
        assert "places" in result
        if result["count"] > 0:
            assert "distance_m" in result["places"][0]
