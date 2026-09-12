"""
zone/state_machine.py — Deterministic safety state machine.

Anti-flicker policy:
* Escalation (more severe candidate) commits **immediately**.
* Recovery (less severe candidate) must persist for ``stability_frames``
  consecutive cycles before committing.
* FAULT and CRITICAL always commit immediately.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.models import Zone


@dataclass
class StateUpdate:
    state: Zone
    changed: bool
    from_state: Zone


class SafetyStateMachine:
    def __init__(self, stability_frames: int = 3,
                 immediate_zones: tuple[Zone, ...] = (Zone.FAULT, Zone.CRITICAL),
                 initial: Zone = Zone.UNKNOWN) -> None:
        self._stability = max(1, int(stability_frames))
        self._immediate = set(immediate_zones)
        self._state = initial
        self._candidate: Zone | None = None
        self._count = 0

    @property
    def state(self) -> Zone:
        return self._state

    def update(self, candidate: Zone) -> StateUpdate:
        """Feed a candidate state; returns the committed state + change flag."""
        prev = self._state

        if candidate in self._immediate:
            self._state = candidate
            self._candidate = None
            self._count = 0
            return StateUpdate(self._state, candidate != prev, prev)

        if candidate.severity > self._state.severity:
            # Escalation is immediate (safe fail-fast direction).
            self._state = candidate
            self._candidate = None
            self._count = 0
            return StateUpdate(self._state, True, prev)

        if candidate == self._state:
            self._candidate = None
            self._count = 0
            return StateUpdate(self._state, False, prev)

        # Recovery: require persistence.
        if candidate == self._candidate:
            self._count += 1
        else:
            self._candidate = candidate
            self._count = 1

        if self._count >= self._stability:
            self._state = candidate
            self._candidate = None
            self._count = 0
            return StateUpdate(self._state, True, prev)

        return StateUpdate(self._state, False, prev)

    def reset(self, initial: Zone = Zone.UNKNOWN) -> None:
        self._state = initial
        self._candidate = None
        self._count = 0