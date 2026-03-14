"""Intent-based LOD controller for NovaTour.

Detects user intent to change verbosity level and returns the target LOD.
Simplified from iMeanPiper IntelligentLODController - rule-based only (no LLM calls).
"""

import re
from typing import Optional

# Patterns that signal the user wants less detail
BRIEF_PATTERNS = [
    r"\bbe\s+brief\b",
    r"\bshort(er)?\b",
    r"\bquick(ly)?\b",
    r"\bjust\s+tell\b",
    r"\btoo\s+(long|much|detailed|verbose)\b",
    r"\bsummar(y|ize)\b",
    r"\btl;?dr\b",
    r"\bless\s+detail\b",
    r"\bkeep\s+it\s+simple\b",
    r"\bget\s+to\s+the\s+point\b",
    # Chinese
    r"简[短单]",
    r"太长",
    r"简单[点说]",
    r"快[点说]",
]

# Patterns that signal the user wants more detail
DETAIL_PATTERNS = [
    r"\btell\s+me\s+more\b",
    r"\bmore\s+detail(s|ed)?\b",
    r"\belaborate\b",
    r"\bexplain\s+(more|further|in\s+detail)\b",
    r"\bgo\s+(deeper|on|into\s+detail)\b",
    r"\bwhat\s+else\b",
    r"\bfull\s+story\b",
    r"\bnarrat(e|ive|ion)\b",
    r"\bpodcast\s+mode\b",
    r"\bimmersive\b",
    # Chinese
    r"[详多]说",
    r"展开[说讲]",
    r"完整",
    r"继续[说讲]",
]


def detect_lod_change(user_text: str, current_lod: int) -> int:
    """Detect if user wants to change LOD level based on their input.

    Args:
        user_text: The user's input text
        current_lod: Current LOD level (1, 2, or 3)

    Returns:
        Target LOD level (1, 2, or 3). Same as current if no change detected.
    """
    text = user_text.lower().strip()

    # Check for brief intent
    for pattern in BRIEF_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return max(1, current_lod - 1) if current_lod > 1 else 1

    # Check for detail intent
    for pattern in DETAIL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return min(3, current_lod + 1) if current_lod < 3 else 3

    return current_lod


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
