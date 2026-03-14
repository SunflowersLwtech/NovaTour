"""Tests for NovaTour LOD system (Phase 6).

Tests LOD config, cold start, intent detection, and prompt builder.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.lod.cold_start import get_initial_lod
from app.lod.config import LOD_1_CONFIG, LOD_2_CONFIG, LOD_3_CONFIG, LOD_CONFIGS
from app.lod.controller import detect_lod_change, get_lod_transition_phrase
from app.lod.prompt_builder import build_system_prompt


# ── Config Tests ─────────────────────────────────────────────


def test_lod_configs_exist():
    assert 1 in LOD_CONFIGS
    assert 2 in LOD_CONFIGS
    assert 3 in LOD_CONFIGS


def test_lod_1_config():
    c = LOD_1_CONFIG
    assert c.lod == 1
    assert c.min_words == 15
    assert c.max_words == 40
    assert c.target_words == 27


def test_lod_2_config():
    c = LOD_2_CONFIG
    assert c.lod == 2
    assert c.min_words == 80
    assert c.max_words == 150


def test_lod_3_config():
    c = LOD_3_CONFIG
    assert c.lod == 3
    assert c.min_words == 400
    assert c.max_words == 800


# ── Cold Start Tests ─────────────────────────────────────────


def test_cold_start_returns_lod_2():
    assert get_initial_lod() == 2


# ── LOD Controller / Detection Tests ────────────────────────


def test_brief_detection():
    assert detect_lod_change("be brief please", 2) == 1
    assert detect_lod_change("too long", 3) == 2
    assert detect_lod_change("keep it simple", 2) == 1
    assert detect_lod_change("太长了", 3) == 2


def test_detail_detection():
    assert detect_lod_change("tell me more about this", 2) == 3
    assert detect_lod_change("elaborate on that", 1) == 2
    assert detect_lod_change("podcast mode", 2) == 3
    assert detect_lod_change("详说一下", 1) == 2


def test_no_change_detection():
    assert detect_lod_change("what is the weather", 2) == 2
    assert detect_lod_change("search for flights to Tokyo", 1) == 1
    assert detect_lod_change("plan my trip", 3) == 3
    assert detect_lod_change("Tell me one quick travel tip for Bangkok.", 2) == 2


def test_lod_boundaries():
    # Can't go below 1
    assert detect_lod_change("be brief", 1) == 1
    # Can't go above 3
    assert detect_lod_change("tell me more", 3) == 3


# ── Transition Phrases ───────────────────────────────────────


def test_transition_phrase_en():
    phrase = get_lod_transition_phrase(2, 3, "en")
    assert phrase is not None
    assert "story" in phrase.lower()


def test_transition_phrase_no_change():
    assert get_lod_transition_phrase(2, 2) is None


def test_transition_phrase_zh():
    phrase = get_lod_transition_phrase(2, 3, "zh")
    assert phrase is not None


# ── Prompt Builder Tests ─────────────────────────────────────


def test_build_system_prompt_default():
    prompt = build_system_prompt()
    assert "NovaTour" in prompt
    assert "Level 2" in prompt
    assert "search_flights" in prompt


def test_build_system_prompt_lod1():
    prompt = build_system_prompt(lod_level=1)
    assert "Level 1" in prompt
    assert "Quick answer" in prompt


def test_build_system_prompt_lod3_has_podcast():
    prompt = build_system_prompt(lod_level=3)
    assert "Level 3" in prompt
    assert "Narrative" in prompt or "narration" in prompt.lower()
    assert "podcast" in prompt.lower() or "immersive" in prompt.lower()


def test_build_system_prompt_invalid_clamps_to_range():
    prompt = build_system_prompt(lod_level=99)
    assert "Level 3" in prompt  # clamped to max=3
    prompt = build_system_prompt(lod_level=-1)
    assert "Level 1" in prompt  # clamped to min=1
