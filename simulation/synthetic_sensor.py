"""
simulation/synthetic_sensor.py — Scenario-driven ultrasonic sensor.

Builds a :class:`MockUltrasonicSensor` whose provider follows the
scenario timeline relative to a run *origin* (wall time when the
simulation started), plus realistic noise.
"""

from __future__ import annotations

from typing import Optional

from distance.ultrasonic import MockUltrasonicSensor, SensorConfig
from simulation.scenario import Scenario


def build_sensor(scenario: Scenario,
                 sensor_cfg: dict | None = None,
                 origin: float = 0.0,
                 noise_m: float = 0.02,
                 fault_probability: float = 0.0) -> MockUltrasonicSensor:
    cfg = sensor_cfg or {}
    config = SensorConfig(
        min_range_m=float(cfg.get("min_range_m", 0.05)),
        max_range_m=float(cfg.get("max_range_m", 4.5)),
        timeout_s=float(cfg.get("timeout_s", 0.5)),
        median_window=int(cfg.get("median_window", 5)),
    )

    def provider(now: float) -> tuple[Optional[float], bool]:
        t = max(0.0, now - origin)
        return scenario.sensor_distance(t)

    return MockUltrasonicSensor(
        provider=provider,
        config=config,
        noise_m=noise_m,
        fault_probability=fault_probability,
    )