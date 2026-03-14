"""
Voice State Machine for Nova Sonic agent responses.

Manages the lifecycle of agent voice responses, tracking whether the agent
is idle, actively speaking, was interrupted by the user, or has finished
its response. Adapted from the podcast state machine pattern for real-time
voice interaction with Nova Sonic.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class VoiceState(Enum):
    """
    Agent voice response states.

    State transitions:
    - IDLE → RESPONDING:    First audio chunk received from agent
    - RESPONDING → INTERRUPTED: User interruption event
    - RESPONDING → FINISHED:    Agent completes its response
    - INTERRUPTED → RESPONDING:  New response starts after interruption
    - INTERRUPTED → IDLE:        Reset after interruption
    - FINISHED → RESPONDING:     New response starts
    - FINISHED → IDLE:           Reset after completion
    """

    IDLE = "idle"
    RESPONDING = "responding"
    INTERRUPTED = "interrupted"
    FINISHED = "finished"


@dataclass
class VoiceStateMachine:
    """
    State machine for managing agent voice response lifecycle.

    Validates transitions, tracks state history, and provides convenience
    methods for common voice events. Invalid transitions are logged as
    warnings and silently ignored.
    """

    session_id: str
    _current_state: VoiceState = field(default=VoiceState.IDLE, init=False)
    _state_history: List[Dict[str, object]] = field(default_factory=list, init=False)

    # Valid state transitions
    VALID_TRANSITIONS: Dict[VoiceState, List[VoiceState]] = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        self.VALID_TRANSITIONS = {
            VoiceState.IDLE: [VoiceState.RESPONDING],
            VoiceState.RESPONDING: [VoiceState.INTERRUPTED, VoiceState.FINISHED],
            VoiceState.INTERRUPTED: [VoiceState.RESPONDING, VoiceState.IDLE],
            VoiceState.FINISHED: [VoiceState.RESPONDING, VoiceState.IDLE],
        }
        self._record_state_change(VoiceState.IDLE, "initialized")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> VoiceState:
        """Return the current voice state."""
        return self._current_state

    @property
    def state_history(self) -> List[Dict[str, object]]:
        """Return a copy of the state history."""
        return self._state_history.copy()

    # ------------------------------------------------------------------
    # Core transition logic
    # ------------------------------------------------------------------

    def can_transition_to(self, new_state: VoiceState) -> bool:
        """Check whether a transition to *new_state* is valid."""
        valid_next = self.VALID_TRANSITIONS.get(self._current_state, [])
        return new_state in valid_next

    def transition(self, event: str) -> VoiceState:
        """
        Validate and perform a state transition based on *event*.

        Supported events:
            ``audio_chunk``       — first audio chunk received
            ``interruption``      — user interrupted the agent
            ``response_complete`` — agent finished its response
            ``reset``             — return to IDLE

        If the transition is invalid for the current state the event is
        ignored and a warning is logged.  The current state is always
        returned regardless of whether the transition succeeded.
        """
        target = self._event_to_state(event)
        if target is None:
            logger.warning(
                "[VoiceState:%s] Unknown event '%s' in state %s",
                self.session_id,
                event,
                self._current_state.value,
            )
            return self._current_state

        if not self.can_transition_to(target):
            valid_next = self.VALID_TRANSITIONS.get(self._current_state, [])
            logger.warning(
                "[VoiceState:%s] Invalid transition: %s -> %s "
                "(event=%s, valid targets: %s)",
                self.session_id,
                self._current_state.value,
                target.value,
                event,
                [s.value for s in valid_next],
            )
            return self._current_state

        old_state = self._current_state
        self._current_state = target
        self._record_state_change(target, event, old_state)

        logger.info(
            "[VoiceState:%s] %s -> %s (event=%s)",
            self.session_id,
            old_state.value,
            target.value,
            event,
        )
        return self._current_state

    def reset(self) -> VoiceState:
        """Reset the state machine back to IDLE."""
        if self._current_state == VoiceState.IDLE:
            return self._current_state
        return self.transition("reset")

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def on_audio_chunk(self) -> VoiceState:
        """Signal that an audio chunk was received from the agent."""
        return self.transition("audio_chunk")

    def on_interruption(self) -> VoiceState:
        """Signal that the user interrupted the agent."""
        return self.transition("interruption")

    def on_response_complete(self) -> VoiceState:
        """Signal that the agent finished its response."""
        return self.transition("response_complete")

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def is_idle(self) -> bool:
        return self._current_state == VoiceState.IDLE

    def is_responding(self) -> bool:
        return self._current_state == VoiceState.RESPONDING

    def is_interrupted(self) -> bool:
        return self._current_state == VoiceState.INTERRUPTED

    def is_finished(self) -> bool:
        return self._current_state == VoiceState.FINISHED

    def get_state_summary(self) -> Dict[str, object]:
        """Return a dictionary summarising the current state."""
        return {
            "session_id": self.session_id,
            "current_state": self._current_state.value,
            "valid_next_states": [
                s.value
                for s in self.VALID_TRANSITIONS.get(self._current_state, [])
            ],
            "state_changes": len(self._state_history),
            "last_change": self._state_history[-1] if self._state_history else None,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _event_to_state(self, event: str) -> Optional[VoiceState]:
        """Map an event name to its target state."""
        mapping: Dict[str, VoiceState] = {
            "audio_chunk": VoiceState.RESPONDING,
            "interruption": VoiceState.INTERRUPTED,
            "response_complete": VoiceState.FINISHED,
            "reset": VoiceState.IDLE,
        }
        return mapping.get(event)

    def _record_state_change(
        self,
        new_state: VoiceState,
        reason: str,
        old_state: Optional[VoiceState] = None,
    ) -> None:
        """Append a state-change record to the history."""
        self._state_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "old_state": old_state.value if old_state else None,
                "new_state": new_state.value,
                "reason": reason,
            }
        )

    def __repr__(self) -> str:
        return (
            f"VoiceStateMachine(session={self.session_id!r}, "
            f"state={self._current_state.value!r})"
        )
