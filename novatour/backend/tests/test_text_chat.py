"""REST chat API tests for NovaTour.

Tests the POST /api/chat endpoint for basic functionality,
session propagation, and error handling.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_chat_basic_response():
    """POST /api/chat returns a non-empty reply."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello, what can you help me with?"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert len(data["reply"]) > 0


@pytest.mark.asyncio
async def test_chat_session_propagation():
    """Session ID is echoed back in the response."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/chat",
            json={"message": "Hi", "session_id": "test-session-42"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "test-session-42"


@pytest.mark.asyncio
async def test_chat_error_graceful():
    """Even on error, returns a graceful fallback message."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/chat",
            json={"message": ""},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert len(data["reply"]) > 0
