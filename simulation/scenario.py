"""
simulation/scenario.py — Scenario definition and registry.

A Scenario is a fully time-parameterised description of sensor/vision/
camera behaviour.  ``t`` is seconds since the scenario started.  All
scenarios are deterministic, so simulation tests are reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from core.models import Zone

# (t) -> (distance_m | None, valid)
SensorFn = Callable[[float], tuple[Optional[float], bool]]
# (t) -> distance_m | None  (None = no object visible to vision)
VisionFn = Callable[[float], Optional[float]]


@dataclass
class Scenario:
    name: str
    description: str
    duration_s: float
    sensor_distance: SensorFn
    vision_distance: VisionFn
    vision_confidence: Callable[[float], float] = field(default=lambda t: 0.90)
    camera_healthy: Callable[[float], bool] = field(default=lambda t: True)
    obj_width_m: float = 1.8
    center_frac_x: Callable[[float], float] = field(default=lambda t: 0.5)
    expected_states: list[Zone] = field(default_factory=list)
    notes: str = ""


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def linear(d0: float, d1: float, t0: float, t1: float) -> SensorFn:
    """Distance that moves linearly from d0 (at t0) to d1 (at t1)."""
    span = max(1e-6, t1 - t0)

    def fn(t: float) -> tuple[Optional[float], bool]:
        if t <= t0:
            return d0, True
        if t >= t1:
            return d1, True
        frac = (t - t0) / span
        return d0 + (d1 - d0) * frac, True

    return fn


def constant(value: float) -> SensorFn:
    def fn(t: float) -> tuple[Optional[float], bool]:
        return value, True

    return fn


def invalid_after(t_fail: float) -> SensorFn:
    def fn(t: float) -> tuple[Optional[float], bool]:
        return (None, False) if t >= t_fail else (3.0, True)

    return fn


def sensor_to_vision(sensor: SensorFn) -> VisionFn:
    """Vision distance mirrors the sensor timeline (same truth)."""
    def fn(t: float) -> Optional[float]:
        distance, valid = sensor(t)
        return distance if valid else None

    return fn


def make_scenario(name: str, description: str, duration_s: float,
                  sensor: SensorFn, vision: VisionFn,
                  expected: list[str] | None = None, **kwargs) -> Scenario:
    return Scenario(
        name=name,
        description=description,
        duration_s=duration_s,
        sensor_distance=sensor,
        vision_distance=vision,
        expected_states=[Zone(s.upper()) for s in (expected or [])],
        **kwargs,
    )


SCENARIOS: dict[str, Scenario] = {}


def register(scenario: Scenario) -> Scenario:
    SCENARIOS[scenario.name] = scenario
    return scenario


def get_scenario(name: str | None) -> Scenario:
    """Look up a scenario; defaults to the fast-approach scenario."""
    if not name:
        return SCENARIOS["vehicle_approaching_fast"]
    if name not in SCENARIOS:
        raise KeyError(
            f"Unknown scenario {name!r}. Available: {sorted(SCENARIOS)}"
        )
    return SCENARIOS[name]