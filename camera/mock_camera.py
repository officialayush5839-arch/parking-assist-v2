"""
camera/mock_camera.py — Mock/synthetic camera.

Generates BGR frames with numpy (no OpenCV needed): a grey gradient plus
an optional foreground blob whose size/position follows a provider.  The
provider returns ``None`` to simulate a camera failure (no frame).
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from camera.interface import CameraInterface

# provider(now_wall) -> np.ndarray | None
FrameProvider = Callable[[float], Optional[np.ndarray]]


class MockCamera(CameraInterface):
    def __init__(self, width: int = 640, height: int = 480,
                 provider: Optional[FrameProvider] = None) -> None:
        self._width = width
        self._height = height
        self._provider = provider or (lambda now: MockCamera._base_frame(width, height))
        self._running = False

    @property
    def healthy(self) -> bool:
        return self._running

    def set_provider(self, provider: FrameProvider) -> None:
        self._provider = provider

    def start(self) -> None:
        self._running = True

    def read(self) -> Optional[np.ndarray]:
        if not self._running:
            return None
        try:
            return self._provider(_wall())
        except Exception:
            return None

    def stop(self) -> None:
        self._running = False

    def get_resolution(self) -> tuple[int, int]:
        return (self._width, self._height)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def base_frame(width: int = 640, height: int = 480) -> np.ndarray:
        return MockCamera._base_frame(width, height)

    @staticmethod
    def scene_frame(now: float, vision_distance_m: Optional[float],
                    width: int = 640, height: int = 480,
                    focal_px: float = 600.0, obj_width_m: float = 1.8,
                    label_y: float = 0.55) -> np.ndarray:
        """Render a grey scene with a rectangle whose pixel width maps to
        *vision_distance_m* through the pinhole formula (inverse), so the
        mock "detector" can re-estimate the distance consistently."""
        frame = MockCamera._base_frame(width, height)
        if vision_distance_m is None or vision_distance_m <= 0:
            return frame
        box_w_px = int((obj_width_m * focal_px) / vision_distance_m)
        box_w_px = max(8, min(int(width * 0.9), box_w_px))
        box_h_px = int(box_w_px * 0.6)
        x1 = (width - box_w_px) // 2
        y1 = int(height * label_y) - box_h_px // 2
        y1 = max(0, y1)
        color = (180, 160, 140)  # BGR-ish grey body
        frame[y1:y1 + box_h_px, x1:x1 + box_w_px] = color
        # Slight shading so the box is visible against the gradient.
        frame[y1:y1 + box_h_px, x1:x1 + box_w_px] += np.array([10, 10, 10], dtype=np.uint8)
        return frame

    @staticmethod
    def _base_frame(width: int, height: int) -> np.ndarray:
        yy = np.linspace(60, 130, height, dtype=np.uint8).reshape(-1, 1)
        xx = np.linspace(40, 110, width, dtype=np.uint8).reshape(1, -1)
        base = (yy + xx) // 2
        return np.stack([base, base, base], axis=2).astype(np.uint8)


def _wall() -> float:
    import time  # noqa: PLC0415

    return time.time()