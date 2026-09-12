"""
alerts/scheduler.py — Non-blocking alert scheduler.

Drives the LED bank and buzzer from the committed safety state using wall
time only — never sleeps, never blocks the safety loop.  LED output is
steady per zone; the buzzer follows the zone pattern.
"""

from __future__ import annotations

from typing import Optional

from alerts.buzzer_controller import (
    BuzzerInterface,
    BuzzerPattern,
    DEFAULT_PATTERNS,
)
from alerts.led_controller import ZoneLEDMapper
from core.models import Zone


class AlertScheduler:
    def __init__(self, led_mapper: ZoneLEDMapper, buzzer: Optional[BuzzerInterface],
                 patterns: Optional[dict[Zone, Optional[BuzzerPattern]]] = None,
                 buzzer_enabled: bool = True) -> None:
        self._led = led_mapper
        self._buzzer = buzzer
        self._patterns = patterns or DEFAULT_PATTERNS
        self._buzzer_enabled = buzzer_enabled
        self._last_state: Optional[Zone] = None
        self._state_since: float = 0.0

    def update(self, state: Zone, now: float) -> None:
        """Apply *state* to LEDs and buzzer (idempotent, non-blocking)."""
        if state != self._last_state:
            self._last_state = state
            self._state_since = now

        self._led.update(state)

        if self._buzzer is None or not self._buzzer_enabled:
            return
        pattern = self._patterns.get(state)
        if pattern is None:
            self._buzzer.off()
            return
        phase = now - self._state_since
        if pattern.is_on(phase):
            self._buzzer.on()
        else:
            self._buzzer.off()

    def reset(self) -> None:
        self._last_state = None
        if self._buzzer is not None:
            self._buzzer.off()