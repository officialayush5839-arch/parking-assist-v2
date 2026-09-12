"""
vision/mock_detector.py — Mock detector (SIMULATION).

Produces scripted detections from an injected provider.  All output is
clearly MOCK — it must never be presented as real ML results.  The
provider signature is ``provider(now_wall) -> list[Detection] | None``.
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from core.models import Detection
from vision.detector import DetectorBackend

# provider(now_wall) -> list of (class_name, confidence, bbox) or None
DetectionProvider = Callable[[float], Optional[list[tuple[str, float, tuple[int, int, int, int]]]]]


class MockDetector(DetectorBackend):
    def __init__(self, provider: Optional[DetectionProvider] = None) -> None:
        self._provider = provider or (lambda now: None)
        self._ready = True

    @property
    def name(self) -> str:
        return "mock"

    def set_provider(self, provider: DetectionProvider) -> None:
        self._provider = provider

    def initialize(self) -> None:
        self._ready = True

    def detect(self, frame: np.ndarray, timestamp: float,
               frame_id: int) -> list[Detection]:
        if not self._ready:
            return []
        raw = self._provider(timestamp)
        if not raw:
            return []
        return [
            Detection(
                class_name=class_name,
                confidence=min(1.0, max(0.0, float(conf))),
                bbox=(int(x1), int(y1), int(x2), int(y2)),
                timestamp=timestamp,
                frame_id=frame_id,
            )
            for class_name, conf, (x1, y1, x2, y2) in raw
        ]

    def shutdown(self) -> None:
        self._ready = False