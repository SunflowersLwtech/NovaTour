"""Comprehensive tests for newly migrated modules.

Tests: LOD signal detection (priority-based), intent classification,
LOD state management, TTS sanitization, voice state machine, cold start.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.lod.cold_start import get_initial_lod
from app.lod.controller import (
    LODSignal,
    SignalType,
    _PATTERN_GROUPS,
    detect_lod_change,
    detect_lod_signal,
    get_lod_transition_phrase,
)
from app.lod.intent import IntentType, rule_based_intent_classification
from app.lod.state import LODState
from app.utils.tts_sanitize import sanitize_for_tts
from app.voice.voice_state import VoiceState, VoiceStateMachine


# ════════════════════════════════════════════════════════════════
# LOD Signal Detection (Priority-Based)
# ════════════════════════════════════════════════════════════════


class TestLODSignalDetection:
    """Tests for the upgraded priority-based signal detection."""

    def test_explicit_down_highest_priority(self):
        """Explicit DOWN should beat implicit UP in mixed input."""
        # "keep it short" is explicit down, "interesting" is implicit up
        signal = detect_lod_signal("keep it short, that's interesting")
        assert signal.direction == "down"
        assert signal.signal_type == SignalType.EXPLICIT

    def test_explicit_up_beats_implicit_down(self):
        """Explicit UP should beat implicit DOWN."""
        signal = detect_lod_signal("tell me more even though it was too long")
        assert signal.direction == "up"
        assert signal.signal_type == SignalType.EXPLICIT

    def test_explicit_down_en(self):
        for phrase in ["keep it short", "summarize", "be brief", "tl;dr", "less detail"]:
            signal = detect_lod_signal(phrase)
            assert signal.direction == "down", f"Failed for: {phrase}"
            assert signal.signal_type == SignalType.EXPLICIT

    def test_explicit_down_zh(self):
        for phrase in ["简单说", "总结一下", "长话短说", "简洁点"]:
            signal = detect_lod_signal(phrase)
            assert signal.direction == "down", f"Failed for: {phrase}"

    def test_explicit_up_en(self):
        for phrase in ["tell me more", "elaborate", "go into detail", "podcast mode"]:
            signal = detect_lod_signal(phrase)
            assert signal.direction == "up", f"Failed for: {phrase}"
            assert signal.signal_type == SignalType.EXPLICIT

    def test_explicit_up_zh(self):
        for phrase in ["详细讲讲", "展开说说", "多说一点", "详说一下"]:
            signal = detect_lod_signal(phrase)
            assert signal.direction == "up", f"Failed for: {phrase}"

    def test_implicit_down(self):
        for phrase in ["too long", "get to the point", "太长了", "说重点"]:
            signal = detect_lod_signal(phrase)
            assert signal.direction == "down", f"Failed for: {phrase}"
            assert signal.signal_type == SignalType.IMPLICIT

    def test_implicit_up(self):
        for phrase in ["interesting", "go on", "what else", "还有呢"]:
            signal = detect_lod_signal(phrase)
            assert signal.direction == "up", f"Failed for: {phrase}"
            assert signal.signal_type == SignalType.IMPLICIT

    def test_no_signal(self):
        """Normal travel queries should return no signal."""
        for phrase in [
            "What's the weather in Tokyo?",
            "Find flights to Paris",
            "东京天气怎么样",
        ]:
            signal = detect_lod_signal(phrase)
            assert signal.direction == "none", f"False positive for: {phrase}"

    def test_confidence_ranges(self):
        """All signal confidences should be in [0, 1]."""
        signal = detect_lod_signal("keep it short")
        assert 0.0 <= signal.confidence <= 1.0

    def test_trigger_phrase_captured(self):
        signal = detect_lod_signal("Can you elaborate on that?")
        assert signal.trigger_phrase is not None
        assert "elaborate" in signal.trigger_phrase

    def test_case_insensitive(self):
        signal = detect_lod_signal("TELL ME MORE")
        assert signal.direction == "up"

    def test_detect_lod_change_backward_compat(self):
        """detect_lod_change() should still work as a thin wrapper."""
        assert detect_lod_change("keep it short", 2) == 1
        assert detect_lod_change("tell me more", 2) == 3
        assert detect_lod_change("what's the weather", 2) == 2

    def test_lod_boundary_clamping(self):
        assert detect_lod_change("keep it short", 1) == 1  # can't go below 1
        assert detect_lod_change("tell me more", 3) == 3  # can't go above 3


# ════════════════════════════════════════════════════════════════
# Intent Classification
# ════════════════════════════════════════════════════════════════


class TestIntentClassification:
    """Tests for rule-based intent classification (TYPE_A/B/C)."""

    def test_stop_intent_en(self):
        for phrase in ["stop", "enough", "move on", "never mind", "skip"]:
            intent = rule_based_intent_classification(phrase)
            assert intent == IntentType.STOP, f"Failed for: {phrase}"

    def test_stop_intent_zh(self):
        for phrase in ["够了", "停", "算了", "换个话题"]:
            intent = rule_based_intent_classification(phrase)
            assert intent == IntentType.STOP, f"Failed for: {phrase}"

    def test_lod_change_down_intent(self):
        for phrase in ["keep it short", "summarize", "be brief", "make it quick", "简单说"]:
            intent = rule_based_intent_classification(phrase)
            assert intent == IntentType.LOD_CHANGE, f"Failed for: {phrase}"

    def test_lod_change_up_intent(self):
        for phrase in ["tell me more", "elaborate", "why is that", "详细讲讲"]:
            intent = rule_based_intent_classification(phrase)
            assert intent == IntentType.LOD_CHANGE, f"Failed for: {phrase}"

    def test_normal_qa_intent(self):
        for phrase in [
            "What's the weather in Tokyo?",
            "Find me a hotel",
            "I want to visit Paris",
            "Tell me one quick travel tip for Bangkok.",
        ]:
            intent = rule_based_intent_classification(phrase)
            assert intent == IntentType.NORMAL_QA, f"Failed for: {phrase}"

    def test_stop_priority_over_lod_change(self):
        """STOP should take priority over LOD_CHANGE."""
        intent = rule_based_intent_classification("stop, tell me more later")
        assert intent == IntentType.STOP

    def test_empty_input(self):
        assert rule_based_intent_classification("") == IntentType.NORMAL_QA
        assert rule_based_intent_classification("   ") == IntentType.NORMAL_QA

    def test_case_insensitive(self):
        assert rule_based_intent_classification("STOP") == IntentType.STOP
        assert rule_based_intent_classification("Tell Me More") == IntentType.LOD_CHANGE


# ════════════════════════════════════════════════════════════════
# LOD State Management
# ════════════════════════════════════════════════════════════════


class TestLODState:
    """Tests for LOD state with sequence-based version control."""

    def test_default_state(self):
        state = LODState()
        assert state.current_lod == 2
        assert state.sequence_id == 0

    def test_clamping(self):
        state = LODState(current_lod=5)
        assert state.current_lod == 3
        state = LODState(current_lod=0)
        assert state.current_lod == 1

    def test_increment_sequence(self):
        state = LODState()
        seq1 = state.increment_sequence()
        assert seq1 == 1
        seq2 = state.increment_sequence()
        assert seq2 == 2

    def test_stale_request_detection(self):
        state = LODState()
        state.increment_sequence()  # seq=1
        state.increment_sequence()  # seq=2

        assert state.is_request_stale(0)  # older than current
        assert state.is_request_stale(1)  # older than current
        assert state.is_request_stale(2)  # equal to current (still stale)
        assert not state.is_request_stale(3)  # future (not stale)

    def test_reset(self):
        state = LODState(current_lod=3)
        state.increment_sequence()
        state.increment_sequence()
        state.reset()
        assert state.current_lod == 2
        assert state.sequence_id == 0

    def test_timestamp_updates(self):
        state = LODState()
        t0 = state.last_updated
        time.sleep(0.01)
        state.increment_sequence()
        assert state.last_updated > t0


# ════════════════════════════════════════════════════════════════
# TTS Sanitization
# ════════════════════════════════════════════════════════════════


class TestTTSSanitize:
    """Tests for markdown-to-plain-text sanitization for TTS."""

    def test_bold(self):
        assert sanitize_for_tts("This is **bold** text") == "This is bold text"

    def test_italic(self):
        assert sanitize_for_tts("This is *italic* text") == "This is italic text"

    def test_bold_and_italic(self):
        result = sanitize_for_tts("**Bold** and *italic* together")
        assert result == "Bold and italic together"

    def test_strikethrough(self):
        assert sanitize_for_tts("This is ~~deleted~~ text") == "This is deleted text"

    def test_inline_code(self):
        assert sanitize_for_tts("Use `git commit` now") == "Use git commit now"

    def test_link(self):
        assert sanitize_for_tts("Visit [Google](https://google.com) now") == "Visit Google now"

    def test_header(self):
        assert sanitize_for_tts("# Hello World").strip() == "Hello World"
        assert sanitize_for_tts("### Section").strip() == "Section"

    def test_fenced_code_block_removed(self):
        text = "Before\n```python\nprint('hi')\n```\nAfter"
        result = sanitize_for_tts(text)
        assert "print" not in result
        assert "Before" in result
        assert "After" in result

    def test_block_quote(self):
        result = sanitize_for_tts("> This is a quote")
        assert result.strip() == "This is a quote"

    def test_list_markers_removed(self):
        text = "- Item one\n- Item two\n* Item three"
        result = sanitize_for_tts(text)
        assert "- " not in result
        assert "* " not in result
        assert "Item one" in result

    def test_ordered_list(self):
        text = "1. First\n2. Second"
        result = sanitize_for_tts(text)
        assert "1." not in result
        assert "First" in result

    def test_html_tags_removed(self):
        assert "b" not in sanitize_for_tts("<b>bold</b>") or "bold" in sanitize_for_tts("<b>bold</b>")
        result = sanitize_for_tts("Hello <br/> world")
        assert "<br/>" not in result

    def test_whitespace_collapse(self):
        result = sanitize_for_tts("Hello   world\n\n\nfoo")
        assert "  " not in result

    def test_empty_string(self):
        assert sanitize_for_tts("") == ""
        assert sanitize_for_tts(None) is None

    def test_already_clean(self):
        text = "Tokyo is a beautiful city with great food."
        assert sanitize_for_tts(text) == text

    def test_real_world_assistant_response(self):
        """Simulate a typical LLM response with mixed markdown."""
        text = (
            "Here are the top **3 hotels** in Tokyo:\n\n"
            "1. **Hotel Sunroute** — budget-friendly, near Shinjuku\n"
            "2. **Park Hyatt** — luxury with a [stunning view](https://parkkyatt.com)\n"
            "3. ~~Grand Prince~~ *Cerulean Tower* — great location\n\n"
            "> All prices are per night.\n\n"
            "Would you like me to book one?"
        )
        result = sanitize_for_tts(text)
        assert "**" not in result
        assert "~~" not in result
        assert "[" not in result
        assert ">" not in result
        assert "Hotel Sunroute" in result
        assert "Park Hyatt" in result
        assert "book one" in result


# ════════════════════════════════════════════════════════════════
# Voice State Machine
# ════════════════════════════════════════════════════════════════


class TestVoiceStateMachine:
    """Tests for the voice response state machine."""

    def test_initial_state_is_idle(self):
        sm = VoiceStateMachine(session_id="test")
        assert sm.state == VoiceState.IDLE
        assert sm.is_idle()

    def test_idle_to_responding(self):
        sm = VoiceStateMachine(session_id="test")
        sm.on_audio_chunk()
        assert sm.state == VoiceState.RESPONDING
        assert sm.is_responding()

    def test_responding_to_interrupted(self):
        sm = VoiceStateMachine(session_id="test")
        sm.on_audio_chunk()
        sm.on_interruption()
        assert sm.state == VoiceState.INTERRUPTED
        assert sm.is_interrupted()

    def test_responding_to_finished(self):
        sm = VoiceStateMachine(session_id="test")
        sm.on_audio_chunk()
        sm.on_response_complete()
        assert sm.state == VoiceState.FINISHED
        assert sm.is_finished()

    def test_interrupted_to_responding(self):
        sm = VoiceStateMachine(session_id="test")
        sm.on_audio_chunk()
        sm.on_interruption()
        sm.on_audio_chunk()  # new response starts
        assert sm.state == VoiceState.RESPONDING

    def test_finished_to_responding(self):
        sm = VoiceStateMachine(session_id="test")
        sm.on_audio_chunk()
        sm.on_response_complete()
        sm.on_audio_chunk()  # new response
        assert sm.state == VoiceState.RESPONDING

    def test_invalid_transition_ignored(self):
        sm = VoiceStateMachine(session_id="test")
        # Can't interrupt from IDLE (no valid transition)
        sm.on_interruption()
        assert sm.state == VoiceState.IDLE  # stays IDLE

    def test_idle_to_finished_invalid(self):
        sm = VoiceStateMachine(session_id="test")
        sm.on_response_complete()  # invalid from IDLE
        assert sm.state == VoiceState.IDLE

    def test_reset(self):
        sm = VoiceStateMachine(session_id="test")
        sm.on_audio_chunk()
        sm.on_interruption()
        sm.reset()
        assert sm.state == VoiceState.IDLE

    def test_state_history_tracked(self):
        sm = VoiceStateMachine(session_id="test")
        sm.on_audio_chunk()
        sm.on_response_complete()
        history = sm.state_history
        assert len(history) >= 3  # init + audio_chunk + response_complete

    def test_full_lifecycle(self):
        """Full conversation lifecycle: idle → responding → finished → responding → interrupted → idle."""
        sm = VoiceStateMachine(session_id="lifecycle")
        assert sm.is_idle()

        sm.on_audio_chunk()
        assert sm.is_responding()

        sm.on_response_complete()
        assert sm.is_finished()

        sm.on_audio_chunk()  # new turn
        assert sm.is_responding()

        sm.on_interruption()
        assert sm.is_interrupted()

        sm.reset()
        assert sm.is_idle()

    def test_get_state_summary(self):
        sm = VoiceStateMachine(session_id="summary-test")
        summary = sm.get_state_summary()
        assert summary["session_id"] == "summary-test"
        assert summary["current_state"] == "idle"
        assert "responding" in summary["valid_next_states"]

    def test_multiple_audio_chunks_stay_responding(self):
        """Multiple audio chunks should keep the state as RESPONDING."""
        sm = VoiceStateMachine(session_id="test")
        sm.on_audio_chunk()
        assert sm.is_responding()
        # Another audio chunk while already responding is invalid
        # (RESPONDING → RESPONDING not in valid transitions)
        sm.on_audio_chunk()
        assert sm.is_responding()  # stays responding (invalid transition ignored)


# ════════════════════════════════════════════════════════════════
# Cold Start
# ════════════════════════════════════════════════════════════════


class TestColdStart:
    """Tests for cold start LOD determination."""

    def test_default_returns_lod_2(self):
        assert get_initial_lod() == 2

    def test_no_time_returns_lod_2(self):
        assert get_initial_lod(time_available_minutes=None) == 2

    def test_short_time_returns_lod_1(self):
        assert get_initial_lod(time_available_minutes=3) == 1
        assert get_initial_lod(time_available_minutes=4.9) == 1

    def test_boundary_time(self):
        assert get_initial_lod(time_available_minutes=5) == 2
        assert get_initial_lod(time_available_minutes=5.0) == 2

    def test_long_time_returns_lod_2(self):
        assert get_initial_lod(time_available_minutes=60) == 2


# ════════════════════════════════════════════════════════════════
# Transition Phrases
# ════════════════════════════════════════════════════════════════


class TestTransitionPhrases:
    """Tests for LOD transition phrases."""

    def test_all_transitions_have_phrases(self):
        transitions = [(1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2)]
        for old, new in transitions:
            phrase = get_lod_transition_phrase(old, new, "en")
            assert phrase is not None, f"Missing EN phrase for {old} → {new}"
            phrase_zh = get_lod_transition_phrase(old, new, "zh")
            assert phrase_zh is not None, f"Missing ZH phrase for {old} → {new}"

    def test_no_change_returns_none(self):
        for level in (1, 2, 3):
            assert get_lod_transition_phrase(level, level) is None

    def test_unknown_language_falls_back_to_en(self):
        phrase = get_lod_transition_phrase(2, 3, "fr")
        assert phrase is not None  # falls back to English
