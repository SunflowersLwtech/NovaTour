"""Tests for resilience utilities."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils.resilience import is_recoverable, safe_json_loads


# ── safe_json_loads ──────────────────────────────────────────


def test_safe_json_loads_plain():
    assert safe_json_loads('{"a": 1}') == {"a": 1}


def test_safe_json_loads_fenced():
    text = '```json\n{"a": 1}\n```'
    assert safe_json_loads(text) == {"a": 1}


def test_safe_json_loads_fenced_no_lang():
    text = '```\n{"b": 2}\n```'
    assert safe_json_loads(text) == {"b": 2}


def test_safe_json_loads_embedded():
    text = 'Here is the result:\n{"x": 42}\nDone.'
    assert safe_json_loads(text) == {"x": 42}


def test_safe_json_loads_invalid():
    assert safe_json_loads("not json at all") is None
    assert safe_json_loads("not json", default={}) == {}


# ── is_recoverable ──────────────────────────────────────────


def test_is_recoverable_timeout():
    assert is_recoverable(TimeoutError("Connection timed out")) is True


def test_is_recoverable_connection():
    assert is_recoverable(ConnectionError("Connection refused")) is True


def test_is_recoverable_rate_limit():
    assert is_recoverable(Exception("429 rate_limit exceeded")) is True


def test_is_recoverable_auth():
    assert is_recoverable(Exception("401 Unauthorized")) is False


def test_is_recoverable_forbidden():
    assert is_recoverable(Exception("403 Forbidden")) is False


def test_is_recoverable_unknown():
    # Unknown errors default to recoverable
    assert is_recoverable(RuntimeError("something broke")) is True
