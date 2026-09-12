"""
alerts/led_controller.py — LED status indication.

Zone → colour mapping is configurable (config.yaml → alerts.led_mapping):

    SAFE=green, CAUTION=yellow, WARNING=orange, CRITICAL=red, FAULT=blue

Both a real GPIO bank (lazy import) and a console mock implement the same
interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from core.errors import ComponentUnavailable
from core.models import Zone

LED_COLORS = ("green", "yellow", "orange", "red", "blue", "off")


class LEDInterface(ABC):
    @abstractmethod
    def set_state(self, color: str, on: bool) -> None:
        """Turn one LED colour on/off ('off' is a no-op)."""

    @abstractmethod
    def all_off(self) -> None:
        ...


class MockLEDBank(LEDInterface):
    """Console LED bank; logs transitions (rate-limited per colour)."""

    def __init__(self, event_bus=None) -> None:
        self._state: dict[str, bool] = {}
        self._bus = event_bus
        self._last_log: dict[str, float] = {}

    def set_state(self, color: str, on: bool) -> None:
        if color not in LED_COLORS:
            return
        if self._state.get(color) == on:
            return
        self._state[color] = on
        active = [c for c, v in self._state.items() if v]
        if self._bus is not None:
            from core.events import EventType, Severity

            self._bus.publish(EventType.ALERT_TRIGGERED, Severity.INFO, "led",
                              {"leds": active})

    def all_off(self) -> None:
        self._state = {c: False for c in self._state}

    def active(self) -> list[str]:
        return [c for c, v in self._state.items() if v]


class RealLEDBank(LEDInterface):
    """GPIO LED bank (5V LEDs via MOSFET drivers)."""

    def __init__(self, pin_map: dict[str, int]) -> None:
        try:
            import RPi.GPIO as GPIO  # type: ignore  # noqa: N814
        except ImportError as exc:
            raise ComponentUnavailable("No GPIO library for LED bank") from exc
        self._gpio = GPIO
        self._pin_map = {c: p for c, p in pin_map.items() if c in LED_COLORS}
        self._state: dict[str, bool] = {}
        self._gpio.setmode(self._gpio.BCM)
        for pin in self._pin_map.values():
            self._gpio.setup(pin, self._gpio.OUT)

    def set_state(self, color: str, on: bool) -> None:
        pin = self._pin_map.get(color)
        if pin is None:
            return
        self._gpio.output(pin, self._gpio.HIGH if on else self._gpio.LOW)
        self._state[color] = on

    def all_off(self) -> None:
        for color in list(self._state):
            self.set_state(color, False)


class ZoneLEDMapper:
    """Maps a Zone to LED colours using the configured mapping."""

    def __init__(self, led_bank: LEDInterface,
                 mapping: Optional[dict[str, str]] = None) -> None:
        self._bank = led_bank
        self._mapping = dict(mapping or {
            "safe": "green", "caution": "yellow", "warning": "orange",
            "critical": "red", "fault": "blue", "unknown": "off",
        })

    def update(self, zone: Zone) -> None:
        color = self._mapping.get(zone.value.lower(), "off")
        for candidate in LED_COLORS:
            self._bank.set_state(candidate, candidate == color)