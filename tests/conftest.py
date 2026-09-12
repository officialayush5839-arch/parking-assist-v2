"""
tests/conftest.py — Shared fixtures.

* ``cfg``        — default loaded configuration (session scope).
* ``camera_runtime`` — a Runtime in camera mode with MOCK camera/sensor
  backends (no real hardware, no wall-clock scenario), so tests can drive
  the pipeline with explicit provider functions and simulated time.
"""

from __future__ import annotations

import time
from typing import Optional

import pytest

from app.config import load_config
from app.runtime import Runtime
from core.models import Detection


@pytest.fixture(scope="session")
def cfg() -> object:
    return load_config()


@pytest.fixture
def camera_runtime():
    """Camera-mode runtime with mock camera + mock sensor backends."""
    cfg = load_config(overrides={
        "system": {"mode": "camera", "verbose": False},
        "camera": {"backend": "mock", "width": 640, "height": 480},
        "distance": {"ultrasonic": {"backend": "mock", "enabled": True}},
    })
    rt = Runtime(cfg=cfg, mode="camera")
    yield rt
    rt.shutdown()


class SimTime:
    """Mutable simulated scenario clock; providers read this instead of
    wall time so tests run instantly and deterministically."""

    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def advance(self, dt: float) -> None:
        self.t += dt

    def __call__(self) -> float:
        return self.t


def detection_at(scenario, t: float, frame_id: int) -> list[Detection]:
    """Build the mock-detector output for *scenario* at simulated time *t*."""
    distance = scenario.vision_distance(t)
    if distance is None:
        return []
    box_w = int((scenario.obj_width_m * 600.0) / max(0.2, distance))
    box_w = max(8, min(640, box_w))
    box_h = int(box_w * 0.6)
    cx = int(scenario.center_frac_x(t) * 640)
    x1 = max(0, cx - box_w // 2)
    y1 = max(0, int(480 * 0.45) - box_h // 2)
    return [Detection(
        class_name="person" if scenario.obj_width_m <= 0.7 else "car",
        confidence=scenario.vision_confidence(t),
        bbox=(x1, y1, x1 + box_w, y1 + box_h),
        timestamp=t,
        frame_id=frame_id,
    )]


def run_scenario_on_pipeline(rt: Runtime, scenario, loop_hz: int = 15):
    """Run *scenario* through *rt*'s pipeline using simulated time.

    Returns the list of Telemetry objects produced.
    """
    clock = SimTime()
    dt = 1.0 / loop_hz

    rt.detector.set_mock_provider(lambda now: [
        (d.class_name, d.confidence, d.bbox) for d in detection_at(scenario, clock.t, 0)
    ])
    rt.sensor.set_provider(lambda now: scenario.sensor_distance(clock.t))

    rt.pipeline.reset()
    telemetry = []
    while clock.t <= scenario.duration_s:
        reading = rt.sensor_reader.read()
        frame = None if not scenario.camera_healthy(clock.t) else rt.camera.read()
        tel = rt.pipeline.step(
            frame=frame,
            frame_id=int(clock.t * loop_hz),
            frame_ts=clock.t,
            sensor_reading=reading,
            camera_healthy=scenario.camera_healthy(clock.t),
            predictor_note="deterministic_ttc",
        )
        telemetry.append(tel)
        clock.advance(dt)
    return telemetry