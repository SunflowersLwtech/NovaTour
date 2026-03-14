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
    structure="Single sentence, core fact",
    system_prompt=(
        "Minimal mode: State only the most essential fact, no elaboration, no explanation. "
        "Convey information in the most concise way possible."
    ),
    tts_instructions="Speak efficiently. Fast pace. Professional tone. No filler words.",
)

LOD_2_CONFIG = LODConfig(
    lod=2,
    word_range=(80, 150),
    structure="Introduction + key points + guidance",
    system_prompt=(
        "Balanced mode: Introduction + 2-3 key points + guiding conclusion. "
        "Provide enough information for understanding while staying concise."
    ),
    tts_instructions="Speak clearly. Medium pace. Warm and conversational.",
)

LOD_3_CONFIG = LODConfig(
    lod=3,
    word_range=(400, 800),
    structure="Complete narrative arc",
    system_prompt=(
        "Narrative mode: Unfold in a storytelling manner with beginning, development, and conclusion. "
        "Include background stories, interesting details, and vivid metaphors. "
        "Engage users like telling a story, making information more memorable."
    ),
    tts_instructions=(
        "Speak expressively. Slower, storytelling pace. "
        "Dramatic pauses for effect. Varied intonation."
    ),
)

LOD_CONFIGS: Dict[int, LODConfig] = {
    1: LOD_1_CONFIG,
    2: LOD_2_CONFIG,
    3: LOD_3_CONFIG,
}
