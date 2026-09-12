"""
simulation/simulator.py — Scenario timeline driver.

Owns the simulation clock (an origin wall-time) and exposes providers for
the mock camera, the mock ultrasonic sensor, and the mock detector — all
driven by the scenario's time-parameterised functions.  ``run`` executes
a fixed-duration timeline at the configured loop rate.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

from simulation.scenario import Scenario

CycleHandler = Callable[[float], None]   # (now_wall)


class Simulator:
    def __init__(self, scenario: Scenario, loop_hz: int = 15,
                 width: int = 640, height: int = 480,
                 focal_px: float = 600.0,
                 sensor_noise_m: float = 0.02) -> None:
        self.scenario = scenario
        self._loop_hz = max(1, int(loop_hz))
        self._min_interval = 1.0 / self._loop_hz
        self._width = width
        self._height = height
        self._focal_px = focal_px
        self._sensor_noise = sensor_noise_m
        self._origin: Optional[float] = None

    # ── Clock ─────────────────────────────────────────────────────────────────

    def start(self) -> float:
        """Begin the scenario; returns the origin wall-time."""
        self._origin = time.time()
        return self._origin

    def t(self, now: float) -> float:
        """Scenario time for a wall timestamp."""
        return max(0.0, now - (self._origin or now))

    def remaining(self, now: float) -> float:
        return max(0.0, self.scenario.duration_s - self.t(now))

    # ── Providers ─────────────────────────────────────────────────────────────

    def sensor_provider(self, now: float) -> tuple[Optional[float], bool]:
        """(distance_m, valid) for the mock ultrasonic sensor."""
        return self.scenario.sensor_distance(self.t(now))

    def camera_provider(self, now: float) -> Optional[object]:
        """Frame (or None) for the mock camera."""
        from camera.mock_camera import MockCamera  # noqa: PLC0415

        t = self.t(now)
        if not self.scenario.camera_healthy(t):
            return None
        return MockCamera.scene_frame(
            now=now,
            vision_distance_m=self.scenario.vision_distance(t),
            width=self._width,
            height=self._height,
            focal_px=self._focal_px,
            obj_width_m=self.scenario.obj_width_m,
        )

    def detection_provider(self, now: float) -> Optional[list[tuple]]:
        """Scripted detections matching the scenario's vision timeline.

        Returns raw ``(class_name, confidence, bbox)`` tuples — the
        MockDetector contract — so the pipeline treats them exactly like
        detector output.
        """
        t = self.t(now)
        distance = self.scenario.vision_distance(t)
        if distance is None:
            return None
        box_w = int((self.scenario.obj_width_m * self._focal_px) / max(0.2, distance))
        box_w = max(8, min(int(self._width * 0.9), box_w))
        box_h = int(box_w * 0.6)
        cx = int(self.scenario.center_frac_x(t) * self._width)
        x1 = max(0, cx - box_w // 2)
        y1 = int(self._height * 0.45) - box_h // 2
        y1 = max(0, y1)
        confidence = self.scenario.vision_confidence(t)
        return [(self._class_name(), confidence, (x1, y1, x1 + box_w, y1 + box_h))]

    def _class_name(self) -> str:
        width = self.scenario.obj_width_m
        if width <= 0.7:
            return "person"
        return "car"

    # ── Run loop ──────────────────────────────────────────────────────────────

    def run(self, duration_s: Optional[float] = None,
            on_cycle: Optional[CycleHandler] = None) -> None:
        """Run the scenario timeline for *duration_s* (scenario default if
        None), invoking *on_cycle(now_wall)* at the loop rate."""
        duration = duration_s or self.scenario.duration_s
        origin = self.start()
        deadline = origin + duration
        while True:
            now = time.time()
            if now >= deadline:
                break
            if on_cycle is not None:
                on_cycle(now)
            # Rate-limit; account for handler time.
            next_slot = origin + self.t(now) + self._min_interval
            sleep = next_slot - time.time()
            if sleep > 0:
                time.sleep(sleep)