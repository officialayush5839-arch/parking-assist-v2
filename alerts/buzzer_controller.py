"""
alerts/buzzer_controller.py — Audible alert patterns.

Patterns (configurable, non-blocking):

    SAFE     : off
    CAUTION  : slow periodic beep   (0.20 s on / 0.80 s off)
    WARNING  : faster beep          (0.15 s on / 0.25 s off)
    CRITICAL : rapid / continuous   (0.10 s on / 0.05 s off)
    FAULT    : distinct double-blip (0.05 s on / 0.10 s off, repeated)

The scheduler (alerts/scheduler.py) computes on/off from wall time, so
nothing here blocks the safety loop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from core.errors import ComponentUnavailable
from core.models import Zone


@dataclass(frozen=True)
class BuzzerPattern:
    on_s: float
    off_s: float

    @property
    def period_s(self) -> float:
        return self.on_s + self.off_s

    def is_on(self, phase_s: float) -> bool:
        return (phase_s % self.period_s) < self.on_s


DEFAULT_PATTERNS: dict[Zone, Optional[BuzzerPattern]] = {
    Zone.SAFE: None,
    Zone.CAUTION: BuzzerPattern(0.20, 0.80),
    Zone.WARNING: BuzzerPattern(0.15, 0.25),
    Zone.CRITICAL: BuzzerPattern(0.10, 0.05),
    Zone.FAULT: BuzzerPattern(0.05, 0.10),
    Zone.UNKNOWN: None,
}


class BuzzerInterface(ABC):
    @abstractmethod
    def on(self) -> None:
        ...

    @abstractmethod
    def off(self) -> None:
        ...


class MockBuzzer(BuzzerInterface):
    def __init__(self) -> None:
        self._state = False

    @property
    def is_on(self) -> bool:
        return self._state

    def on(self) -> None:
        self._state = True

    def off(self) -> None:
        self._state = False


class RealBuzzer(BuzzerInterface):
    """5V active buzzer via a transistor/MOSFET on *pin*."""

    def __init__(self, pin: int) -> None:
        try:
            import RPi.GPIO as GPIO  # type: ignore  # noqa: N814
        except ImportError as exc:
            raise ComponentUnavailable("No GPIO library for buzzer") from exc
        self._gpio = GPIO
        self._pin = pin
        self._gpio.setmode(self._gpio.BCM)
        self._gpio.setup(pin, self._gpio.OUT)

    def on(self) -> None:
        self._gpio.output(self._pin, self._gpio.HIGH)

    def off(self) -> None:
        self._gpio.output(self._pin, self._gpio.LOW)