"""Cold start engine for LOD system.

Determines initial LOD level for new sessions.
Supports an optional time constraint: if available time is < 5 minutes,
the session starts at LOD 1 (time-lock constraint from hard_constraints).
Otherwise defaults to LOD 2 (Balanced).
"""

from typing import Optional

# Threshold ported from iMeanPiper hard_constraints.py
_TIME_LOCK_THRESHOLD_MINUTES: int = 5


def get_initial_lod(time_available_minutes: Optional[float] = None) -> int:
    """Get the default LOD level for a new session.

    Args:
        time_available_minutes: Optional remaining time budget in minutes.
            If provided and less than 5, LOD 1 is returned (time-lock).

    Returns:
        Initial LOD level (1 or 2).
    """
    if (
        time_available_minutes is not None
        and time_available_minutes < _TIME_LOCK_THRESHOLD_MINUTES
    ):
        return 1
    return 2
