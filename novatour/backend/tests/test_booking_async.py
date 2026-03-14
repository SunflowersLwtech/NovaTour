"""Tests for NovaTour async booking (Phase 5).

Tests the two-step confirm_booking pattern and cancel functionality.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio

import pytest


@pytest.fixture(autouse=True)
def enable_mock_mode(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "true")
    from app.config import Settings

    mock_settings = Settings()
    monkeypatch.setattr("app.tools.booking.settings", mock_settings)


def test_book_flight_sync_mock():
    """book_flight still works synchronously in mock mode."""
    from app.tools.booking import book_flight

    result = book_flight("Tokyo", "Paris", "April 1 2026")
    assert result["status"] == "found"
    assert result.get("mock") is True
    assert "booking" in result


def test_confirm_booking_returns_immediately():
    """confirm_booking should return immediately with task_id."""
    from app.tools.booking import confirm_booking

    result = confirm_booking("Tokyo", "Paris", "April 1 2026")
    assert result["status"] == "searching"
    assert "task_id" in result
    assert "message" in result


@pytest.mark.asyncio
async def test_confirm_booking_with_callback():
    """confirm_booking should call progress callback."""
    from app.tools.booking import confirm_booking

    events = []

    async def callback(event):
        events.append(event)

    result = confirm_booking(
        "Tokyo", "Paris", "April 1 2026", progress_callback=callback
    )
    assert result["status"] == "searching"

    # Wait for async task to complete
    await asyncio.sleep(3)

    assert len(events) >= 2  # searching + complete
    assert events[0]["status"] == "searching"
    assert events[-1]["status"] == "complete"


def test_cancel_booking_nonexistent():
    """Cancel should return False for non-existent task."""
    from app.tools.booking import cancel_booking

    assert cancel_booking("nonexistent") is False
