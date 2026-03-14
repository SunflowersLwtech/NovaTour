"""Intent-based LOD controller for NovaTour.

Detects user intent to change verbosity level and returns the target LOD.
Upgraded from simple regex to priority-based signal detection with rich results.

Signal detection priority:
  1. Explicit DOWN  (highest confidence — user explicitly wants less)
  2. Explicit UP
  3. Implicit DOWN
  4. Implicit UP
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------

class SignalType(str, Enum):
    """Type of detected signal."""
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    NONE = "none"


@dataclass
class LODSignal:
    """Rich result returned by detect_lod_signal().

    Attributes:
        direction: "up" (want more detail), "down" (want less), or "none".
        signal_type: Whether the trigger was explicit, implicit, or absent.
        confidence: 0.0–1.0 confidence in the detection.
        trigger_phrase: The pattern string that matched, or None.
    """
    direction: str          # "up" | "down" | "none"
    signal_type: SignalType
    confidence: float
    trigger_phrase: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal pattern entry
# ---------------------------------------------------------------------------

@dataclass
class _Pattern:
    """A single phrase pattern with metadata."""
    phrase: str
    direction: str          # "up" | "down"
    signal_type: SignalType
    confidence: float

    def matches(self, text_lower: str) -> bool:
        return self.phrase in text_lower


# ---------------------------------------------------------------------------
# Pattern banks — 4 priority groups
# Priority order: Explicit DOWN > Explicit UP > Implicit DOWN > Implicit UP
# ---------------------------------------------------------------------------

EXPLICIT_DOWN_PATTERNS: List[_Pattern] = [
    # Chinese
    _Pattern("简单说", "down", SignalType.EXPLICIT, 0.95),
    _Pattern("简短点", "down", SignalType.EXPLICIT, 0.95),
    _Pattern("总结一下", "down", SignalType.EXPLICIT, 0.95),
    _Pattern("长话短说", "down", SignalType.EXPLICIT, 0.95),
    _Pattern("简洁点", "down", SignalType.EXPLICIT, 0.95),
    _Pattern("精简一点", "down", SignalType.EXPLICIT, 0.90),
    _Pattern("简单点", "down", SignalType.EXPLICIT, 0.90),
    # English
    _Pattern("keep it short", "down", SignalType.EXPLICIT, 0.95),
    _Pattern("keep it simple", "down", SignalType.EXPLICIT, 0.95),
    _Pattern("summarize", "down", SignalType.EXPLICIT, 0.95),
    _Pattern("be brief", "down", SignalType.EXPLICIT, 0.95),
    _Pattern("sum it up", "down", SignalType.EXPLICIT, 0.90),
    _Pattern("just the key", "down", SignalType.EXPLICIT, 0.90),
    _Pattern("just tell", "down", SignalType.EXPLICIT, 0.90),
    _Pattern("less detail", "down", SignalType.EXPLICIT, 0.90),
    _Pattern("brief", "down", SignalType.EXPLICIT, 0.90),
    _Pattern("shorter", "down", SignalType.EXPLICIT, 0.90),
    _Pattern("tl;dr", "down", SignalType.EXPLICIT, 0.90),
    _Pattern("tldr", "down", SignalType.EXPLICIT, 0.90),
    # Simple command words
    _Pattern("fast", "down", SignalType.EXPLICIT, 0.90),
    _Pattern("speed up", "down", SignalType.EXPLICIT, 0.85),
    _Pattern("faster", "down", SignalType.EXPLICIT, 0.85),
    _Pattern("quick", "down", SignalType.EXPLICIT, 0.85),
]

EXPLICIT_UP_PATTERNS: List[_Pattern] = [
    # Chinese
    _Pattern("详细讲讲", "up", SignalType.EXPLICIT, 0.95),
    _Pattern("展开说说", "up", SignalType.EXPLICIT, 0.95),
    _Pattern("多说一点", "up", SignalType.EXPLICIT, 0.95),
    _Pattern("详细一点", "up", SignalType.EXPLICIT, 0.95),
    _Pattern("说详细点", "up", SignalType.EXPLICIT, 0.95),
    _Pattern("详细说说", "up", SignalType.EXPLICIT, 0.95),
    _Pattern("具体说说", "up", SignalType.EXPLICIT, 0.90),
    _Pattern("详说", "up", SignalType.EXPLICIT, 0.90),
    _Pattern("完整", "up", SignalType.EXPLICIT, 0.90),
    # English
    _Pattern("tell me more", "up", SignalType.EXPLICIT, 0.95),
    _Pattern("go into detail", "up", SignalType.EXPLICIT, 0.95),
    _Pattern("elaborate", "up", SignalType.EXPLICIT, 0.95),
    _Pattern("expand on", "up", SignalType.EXPLICIT, 0.90),
    _Pattern("more details", "up", SignalType.EXPLICIT, 0.90),
    _Pattern("more detail", "up", SignalType.EXPLICIT, 0.90),
    _Pattern("explain more", "up", SignalType.EXPLICIT, 0.90),
    _Pattern("in detail", "up", SignalType.EXPLICIT, 0.85),
    _Pattern("full story", "up", SignalType.EXPLICIT, 0.85),
    _Pattern("in depth", "up", SignalType.EXPLICIT, 0.85),
    _Pattern("immersive", "up", SignalType.EXPLICIT, 0.85),
    _Pattern("podcast mode", "up", SignalType.EXPLICIT, 0.85),
    # Simple command words
    _Pattern("slow down", "up", SignalType.EXPLICIT, 0.90),
    _Pattern("slow", "up", SignalType.EXPLICIT, 0.85),
    _Pattern("deeper", "up", SignalType.EXPLICIT, 0.85),
]

IMPLICIT_DOWN_PATTERNS: List[_Pattern] = [
    # Chinese
    _Pattern("太长了", "down", SignalType.IMPLICIT, 0.85),
    _Pattern("说重点", "down", SignalType.IMPLICIT, 0.85),
    _Pattern("快点", "down", SignalType.IMPLICIT, 0.75),
    _Pattern("赶时间", "down", SignalType.IMPLICIT, 0.80),
    _Pattern("说完没", "down", SignalType.IMPLICIT, 0.70),
    # English
    _Pattern("too long", "down", SignalType.IMPLICIT, 0.85),
    _Pattern("too much", "down", SignalType.IMPLICIT, 0.80),
    _Pattern("too detailed", "down", SignalType.IMPLICIT, 0.80),
    _Pattern("too verbose", "down", SignalType.IMPLICIT, 0.80),
    _Pattern("get to the point", "down", SignalType.IMPLICIT, 0.85),
    _Pattern("hurry up", "down", SignalType.IMPLICIT, 0.75),
    _Pattern("skip to", "down", SignalType.IMPLICIT, 0.80),
    _Pattern("bottom line", "down", SignalType.IMPLICIT, 0.80),
    # Simple command words
    _Pattern("quickly", "down", SignalType.IMPLICIT, 0.80),
    _Pattern("quicker", "down", SignalType.IMPLICIT, 0.75),
]

IMPLICIT_UP_PATTERNS: List[_Pattern] = [
    # Chinese
    _Pattern("还有呢", "up", SignalType.IMPLICIT, 0.80),
    _Pattern("为什么", "up", SignalType.IMPLICIT, 0.75),
    _Pattern("有意思", "up", SignalType.IMPLICIT, 0.75),
    _Pattern("继续", "up", SignalType.IMPLICIT, 0.75),
    _Pattern("然后呢", "up", SignalType.IMPLICIT, 0.75),
    _Pattern("接着说", "up", SignalType.IMPLICIT, 0.80),
    _Pattern("多说", "up", SignalType.IMPLICIT, 0.75),
    _Pattern("展开讲", "up", SignalType.IMPLICIT, 0.80),
    _Pattern("继续说", "up", SignalType.IMPLICIT, 0.75),
    # English
    _Pattern("why", "up", SignalType.IMPLICIT, 0.70),
    _Pattern("how", "up", SignalType.IMPLICIT, 0.65),
    _Pattern("interesting", "up", SignalType.IMPLICIT, 0.75),
    _Pattern("go on", "up", SignalType.IMPLICIT, 0.75),
    _Pattern("and then", "up", SignalType.IMPLICIT, 0.70),
    _Pattern("what else", "up", SignalType.IMPLICIT, 0.75),
    _Pattern("more", "up", SignalType.IMPLICIT, 0.70),
    # Simple command words
    _Pattern("details", "up", SignalType.IMPLICIT, 0.80),
    _Pattern("narrative", "up", SignalType.IMPLICIT, 0.70),
    _Pattern("narrate", "up", SignalType.IMPLICIT, 0.70),
]

# Ordered list of pattern groups for iteration (priority high → low)
_PATTERN_GROUPS: List[List[_Pattern]] = [
    EXPLICIT_DOWN_PATTERNS,
    EXPLICIT_UP_PATTERNS,
    IMPLICIT_DOWN_PATTERNS,
    IMPLICIT_UP_PATTERNS,
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_lod_signal(user_text: str) -> LODSignal:
    """Detect LOD change signal in user text (rich result).

    Scans all pattern groups in priority order and returns the first match.

    Args:
        user_text: The user's input text.

    Returns:
        LODSignal with direction, signal_type, confidence, and trigger_phrase.
    """
    text_lower = user_text.lower().strip()

    for group in _PATTERN_GROUPS:
        for pattern in group:
            if pattern.matches(text_lower):
                return LODSignal(
                    direction=pattern.direction,
                    signal_type=pattern.signal_type,
                    confidence=pattern.confidence,
                    trigger_phrase=pattern.phrase,
                )

    return LODSignal(
        direction="none",
        signal_type=SignalType.NONE,
        confidence=0.5,
        trigger_phrase=None,
    )


def detect_lod_change(user_text: str, current_lod: int) -> int:
    """Detect if user wants to change LOD level based on their input.

    Backward-compatible thin wrapper around detect_lod_signal().

    Args:
        user_text: The user's input text.
        current_lod: Current LOD level (1, 2, or 3).

    Returns:
        Target LOD level (1, 2, or 3). Same as current if no change detected.
    """
    signal = detect_lod_signal(user_text)

    if signal.direction == "down":
        return max(1, current_lod - 1)
    if signal.direction == "up":
        return min(3, current_lod + 1)
    return current_lod


# ---------------------------------------------------------------------------
# Transition phrasing (unchanged)
# ---------------------------------------------------------------------------

def get_lod_transition_phrase(
    old_lod: int, new_lod: int, language: str = "en"
) -> Optional[str]:
    """Get a transition phrase for LOD changes.

    Args:
        old_lod: Previous LOD level
        new_lod: New LOD level
        language: Language code ("en" or "zh")

    Returns:
        Transition phrase or None if no change
    """
    if old_lod == new_lod:
        return None

    phrases = {
        "en": {
            (2, 1): "Got it, keeping it brief.",
            (3, 1): "Sure, let me be concise.",
            (3, 2): "Alright, I'll balance the detail.",
            (1, 2): "Let me give you a bit more context.",
            (1, 3): "Let me paint the full picture for you.",
            (2, 3): "Let me tell you the whole story...",
        },
        "zh": {
            (2, 1): "好的，简单来说。",
            (3, 1): "好的，简洁地说。",
            (3, 2): "好的，适度地说。",
            (1, 2): "让我多说一些。",
            (1, 3): "让我详细讲讲...",
            (2, 3): "让我慢慢说来...",
        },
    }

    lang_phrases = phrases.get(language, phrases["en"])
    return lang_phrases.get((old_lod, new_lod))
