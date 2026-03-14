"""LOD state management for NovaTour.

Provides a lightweight state container with sequence-based version control
to prevent race conditions in concurrent LOD transitions.

Simplified from iMeanPiper LODState — no narrative position tracking.
"""

import time
from dataclasses import dataclass, field


@dataclass
class LODState:
    """LOD state with version control.

    Attributes:
        current_lod: Current LOD level (1, 2, or 3).
        sequence_id: Monotonic counter incremented on every state change.
        last_updated: Unix timestamp of the most recent update.
    """
    current_lod: int = 2
    sequence_id: int = 0
    last_updated: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        """Clamp LOD to valid range [1, 3]."""
        self.current_lod = max(1, min(3, self.current_lod))

    def increment_sequence(self) -> int:
        """Increment sequence_id and update timestamp.

        Returns:
            The new sequence_id.
        """
        self.sequence_id += 1
        self.last_updated = time.time()
        return self.sequence_id

    def is_request_stale(self, request_seq: int) -> bool:
        """Check whether a transition request is stale.

        A request is stale when its sequence_id is less than or equal to
        the current sequence_id, meaning the state has already moved on.

        Args:
            request_seq: The sequence_id accompanying the transition request.

        Returns:
            True if the request should be rejected as stale.
        """
        return request_seq <= self.sequence_id

    def reset(self) -> None:
        """Reset to default values (new session)."""
        self.current_lod = 2
        self.sequence_id = 0
        self.last_updated = time.time()
