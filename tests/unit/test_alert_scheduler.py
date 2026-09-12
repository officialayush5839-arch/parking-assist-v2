"""Alert scheduler: LED mapping and non-blocking buzzer patterns."""

import time

from alerts.buzzer_controller import DEFAULT_PATTERNS, BuzzerPattern, MockBuzzer
from alerts.led_controller import MockLEDBank, ZoneLEDMapper
from alerts.scheduler import AlertScheduler
from core.models import Zone


def test_led_mapping():
    leds = MockLEDBank()
    mapper = ZoneLEDMapper(leds, {"safe": "green", "critical": "red"})
    mapper.update(Zone.SAFE)
    assert leds.active() == ["green"]
    mapper.update(Zone.CRITICAL)
    assert leds.active() == ["red"]


def test_buzzer_pattern_phase():
    pattern = BuzzerPattern(on_s=0.1, off_s=0.1)
    assert pattern.is_on(0.0)
    assert pattern.is_on(0.05)
    assert not pattern.is_on(0.12)
    assert pattern.is_on(0.21)  # next cycle


def test_critical_is_mostly_on():
    p = DEFAULT_PATTERNS[Zone.CRITICAL]
    assert p is not None
    assert p.on_s / p.period_s > 0.5


def test_safe_buzzer_off():
    buzzer = MockBuzzer()
    scheduler = AlertScheduler(ZoneLEDMapper(MockLEDBank(), {}), buzzer,
                               buzzer_enabled=True)
    scheduler.update(Zone.SAFE, now=0.0)
    assert not buzzer.is_on


def test_warning_beeps_non_blocking():
    buzzer = MockBuzzer()
    scheduler = AlertScheduler(ZoneLEDMapper(MockLEDBank(), {}), buzzer,
                               buzzer_enabled=True)
    now = 1000.0
    scheduler.update(Zone.WARNING, now=now)
    on_states = []
    for i in range(100):
        t = now + i * 0.01
        scheduler.update(Zone.WARNING, t)
        on_states.append(buzzer.is_on)
    assert any(on_states) and not all(on_states)  # periodic, not stuck on