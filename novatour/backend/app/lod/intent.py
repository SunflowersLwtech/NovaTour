"""Intent classification for NovaTour LOD system.

Pure rule-based intent classification — no LLM, no framework dependencies.
Ported from iMeanPiper intent classification (TYPE_A / TYPE_B / TYPE_C).

Intent types:
  NORMAL_QA  — normal interaction (question, follow-up, new topic)
  LOD_CHANGE — user wants to adjust verbosity level (up or down)
  STOP       — user wants to stop / skip / move on
"""

from enum import Enum
from typing import List


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------

class IntentType(str, Enum):
    """Classification of user intent."""
    NORMAL_QA = "NORMAL_QA"
    LOD_CHANGE = "LOD_CHANGE"
    STOP = "STOP"


# ---------------------------------------------------------------------------
# Signal keyword lists
# ---------------------------------------------------------------------------

TYPE_C_STOP_SIGNALS: List[str] = [
    # English
    "enough", "stop", "hold on", "move on", "next topic",
    "that's enough", "i'm done", "never mind", "forget it",
    "don't want to hear", "change topic", "ok enough", "alright enough",
    # Simple command words
    "skip", "pass", "next", "skip it", "pass on this", "skip this",
    # Chinese
    "够了", "停", "算了", "不想听", "换个话题", "下一个",
]

TYPE_B_LOD_UP_SIGNALS: List[str] = [
    # Explicit
    "tell me more", "elaborate", "expand", "more detail", "go into detail",
    "explain more", "give me details", "in depth",
    # Chinese
    "详细讲讲", "展开说说", "多说一点", "详细一点", "具体说说",
    # Implicit
    "why", "interesting", "go on", "what else", "and then",
    "why is that", "how so", "keep going",
    "为什么", "有意思", "还有呢", "然后呢",
    "slow down", "deeper",
]

TYPE_B_LOD_DOWN_SIGNALS: List[str] = [
    # Explicit
    "keep it short", "summarize", "brief", "shorter", "sum it up",
    "just the point", "key points only", "make it quick",
    "be brief", "less detail", "tl;dr", "tldr",
    # Chinese
    "简单说", "总结一下", "简短点", "长话短说", "简洁点", "精简一点",
    # Implicit
    "too long", "get to the point", "hurry up", "bottom line",
    "in a hurry", "don't have time",
    "太长了", "说重点", "快点", "赶时间",
    "speed up",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def rule_based_intent_classification(user_text: str) -> IntentType:
    """Classify user intent using keyword matching (no LLM).

    Priority order:
      1. STOP       — checked first (most urgent)
      2. LOD_CHANGE — checked second
      3. NORMAL_QA  — default

    Args:
        user_text: The user's input text.

    Returns:
        IntentType indicating the classified intent.
    """
    if not user_text or not user_text.strip():
        return IntentType.NORMAL_QA

    text_lower = user_text.lower().strip()

    # 1. Stop signals (highest priority)
    for signal in TYPE_C_STOP_SIGNALS:
        if signal in text_lower:
            return IntentType.STOP

    # 2. LOD change signals (DOWN checked before UP)
    for signal in TYPE_B_LOD_DOWN_SIGNALS:
        if signal in text_lower:
            return IntentType.LOD_CHANGE

    for signal in TYPE_B_LOD_UP_SIGNALS:
        if signal in text_lower:
            return IntentType.LOD_CHANGE

    # 3. Default
    return IntentType.NORMAL_QA
