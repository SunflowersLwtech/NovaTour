"""Declarative conversation definitions for structured E2E tests.

Each conversation is a list of turns with expected outcomes.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Turn:
    """A single conversation turn."""
    utterance: str
    expect_tools: list[str] = field(default_factory=list)
    expect_keywords: list[str] = field(default_factory=list)
    expect_lod: Optional[int] = None
    timeout: float = 30.0


@dataclass
class Conversation:
    """A multi-turn conversation script."""
    name: str
    description: str
    turns: list[Turn]


FULL_TRIP_PLANNING = Conversation(
    name="full_trip_planning",
    description="Complete trip planning flow: greeting → weather → flights → hotels → itinerary",
    turns=[
        Turn(
            utterance="Hi, I'm planning a trip to Tokyo next month.",
            expect_keywords=["tokyo"],
        ),
        Turn(
            utterance="What's the weather like in Tokyo right now?",
            expect_tools=["get_weather"],
            expect_keywords=["temperature", "tokyo"],
        ),
        Turn(
            utterance="Search for flights from New York to Tokyo departing May first.",
            expect_tools=["search_flights"],
            expect_keywords=["flight"],
        ),
        Turn(
            utterance="Find me some hotels in Tokyo.",
            expect_tools=["search_hotels"],
            expect_keywords=["hotel"],
        ),
        Turn(
            utterance="Plan a three day itinerary for Tokyo.",
            expect_tools=["plan_itinerary"],
            expect_keywords=["itinerary", "day"],
            timeout=45.0,
        ),
    ],
)

LOD_ESCALATION = Conversation(
    name="lod_escalation",
    description="Test LOD level changes: normal → detailed → brief",
    turns=[
        Turn(
            utterance="Tell me about Paris.",
            expect_keywords=["paris"],
        ),
        Turn(
            utterance="Tell me much more detail about that.",
            expect_lod=3,
        ),
        Turn(
            utterance="Be brief please, just the highlights.",
            expect_lod=1,
        ),
    ],
)

CORRECTION_AND_CONTEXT = Conversation(
    name="correction_and_context",
    description="Test mid-conversation correction and context retention",
    turns=[
        Turn(
            utterance="Search for flights to Paris.",
            expect_tools=["search_flights"],
            expect_keywords=["paris"],
        ),
        Turn(
            utterance="Actually, I meant London instead of Paris.",
            expect_keywords=["london"],
        ),
        Turn(
            utterance="OK now find hotels there.",
            expect_tools=["search_hotels"],
            expect_keywords=["london"],
        ),
    ],
)

ALL_CONVERSATIONS = [FULL_TRIP_PLANNING, LOD_ESCALATION, CORRECTION_AND_CONTEXT]
