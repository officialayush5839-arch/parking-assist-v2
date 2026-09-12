"""
simulation/synthetic_camera.py — Scenario-driven synthetic camera.

Renders a grey scene with a foreground rectangle whose pixel width maps
to the scenario's vision distance (through the pinhole formula), so the
mock detector and monocular estimator stay mutually consistent.  Returns
``None`` (no frame) while the scenario declares the camera unhealthy.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from camera.mock_camera import MockCamera
from simulation.scenario import Scenario


def build_camera(scenario: Scenario,
                 width: int = 640,
                 height: int = 480,
                 focal_px: float = 600.0,
                 origin: float = 0.0) -> MockCamera:
    def provider(now: float) -> Optional[np.ndarray]:
        t = max(0.0, now - origin)
        if not scenario.camera_healthy(t):
            return None
        distance = scenario.vision_distance(t)
        return MockCamera.scene_frame(
            now=now,
            vision_distance_m=distance,
            width=width,
            height=height,
            focal_px=focal_px,
            obj_width_m=scenario.obj_width_m,
        )

    return MockCamera(width=width, height=height, provider=provider)