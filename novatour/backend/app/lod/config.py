"""LOD Level Configuration for NovaTour.

Simplified from iMeanPiper LOD System.
Defines LOD 1 (Brief), LOD 2 (Standard), LOD 3 (Narrative) levels.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class LODConfig:
    """Configuration for a single LOD level."""

    lod: int
    word_range: Tuple[int, int]
    structure: str
    system_prompt: str
    tts_instructions: str

    @property
    def min_words(self) -> int:
        return self.word_range[0]

    @property
    def max_words(self) -> int:
        return self.word_range[1]

    @property
    def target_words(self) -> int:
        return (self.word_range[0] + self.word_range[1]) // 2


LOD_1_CONFIG = LODConfig(
    lod=1,
    word_range=(15, 40),
    structure="Quick answer",
    system_prompt=(
        "Quick mode: Answer in one sentence. Give the single most useful fact. "
        "Example: 'The best time to visit is spring or fall for mild weather and fewer crowds.' "
        "No elaboration, no follow-up questions, no filler."
    ),
    tts_instructions="Speak efficiently. Fast pace. Confident and direct. Zero filler words.",
)

LOD_2_CONFIG = LODConfig(
    lod=2,
    word_range=(80, 150),
    structure="Conversational summary",
    system_prompt=(
        "Conversational mode: Lead with the key answer, add 2-3 supporting details, "
        "then suggest a natural next step. Sound like a knowledgeable friend chatting. "
        "Example structure: direct answer, why it matters, practical tip, what to explore next."
    ),
    tts_instructions="Speak clearly. Medium pace. Warm, like talking to a friend over coffee.",
)

LOD_3_CONFIG = LODConfig(
    lod=3,
    word_range=(400, 800),
    structure="Immersive narrative",
    system_prompt=(
        "Narrative mode: Tell a story. Transport the listener to the destination. "
        "Use sensory details — what they'll see, hear, smell, taste. "
        "Weave practical information into the narrative naturally. "
        "Structure: a captivating opening, rich middle with local color, and a closing that inspires action."
    ),
    tts_instructions=(
        "Speak expressively like a travel documentary narrator. Slower pace. "
        "Pause before revealing surprising details. Vary your energy — build and release."
    ),
)

LOD_CONFIGS: Dict[int, LODConfig] = {
    1: LOD_1_CONFIG,
    2: LOD_2_CONFIG,
    3: LOD_3_CONFIG,
}
