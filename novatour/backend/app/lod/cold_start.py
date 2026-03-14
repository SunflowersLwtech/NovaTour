"""Cold start engine for LOD system.

Determines initial LOD level for new sessions.
Simplified from iMeanPiper - defaults to LOD 2 (Balanced).
"""


def get_initial_lod() -> int:
    """Get the default LOD level for a new session.

    Returns:
        LOD level (always 2 for cold start)
    """
    return 2
