"""
vision/detector.py — Object-detection abstraction.

Backends implement :class:`DetectorBackend` (initialize/detect/shutdown);
:class:`ObjectDetector` is the wrapper the pipeline uses.  Backend
selection is configurable (``vision.backend``: auto | yolo | tflite |
mock).  When the configured real backend is unavailable, the wrapper
falls back to the MockDetector and publishes DETECTOR_FALLBACK — mock
results are always labelled MOCK.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from core.errors import DetectorUnavailable
from core.events import EventBus, EventType, Severity
from core.models import Detection


class DetectorBackend(ABC):
    """Real detection backend contract."""

    @abstractmethod
    def initialize(self) -> None:
        ...

    @abstractmethod
    def detect(self, frame: np.ndarray, timestamp: float,
               frame_id: int) -> list[Detection]:
        ...

    @abstractmethod
    def shutdown(self) -> None:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class ObjectDetector:
    """Pipeline-facing detector wrapper with mock fallback."""

    def __init__(self, cfg, event_bus: Optional[EventBus] = None) -> None:
        from vision.mock_detector import MockDetector  # noqa: PLC0415

        self._bus = event_bus
        self._backend, self._is_mock, reason = _select_backend(cfg, event_bus)
        try:
            self._backend.initialize()
        except Exception as exc:
            if event_bus is not None:
                event_bus.publish(EventType.DETECTOR_FAILURE, Severity.ERROR,
                                  "vision", {"reason": str(exc)})
            self._backend = MockDetector()
            self._is_mock = True
            reason = str(exc)

        if self._is_mock and event_bus is not None:
            event_bus.publish(EventType.DETECTOR_FALLBACK, Severity.WARNING,
                              "vision", {"reason": reason or "mock backend"})

    @property
    def available(self) -> bool:
        return not self._is_mock

    @property
    def is_mock(self) -> bool:
        return self._is_mock

    @property
    def backend_name(self) -> str:
        return self._backend.name

    def detect(self, frame: Optional[np.ndarray], timestamp: float,
               frame_id: int) -> list[Detection]:
        if frame is None:
            return []
        try:
            return self._backend.detect(frame, timestamp, frame_id)
        except Exception as exc:
            if self._bus is not None:
                self._bus.publish(EventType.DETECTOR_FAILURE, Severity.ERROR,
                                  "vision", {"reason": str(exc)})
            return []

    def set_mock_provider(self, provider) -> None:
        """Wire a scenario provider into the mock backend (simulation)."""
        from vision.mock_detector import MockDetector  # noqa: PLC0415

        if isinstance(self._backend, MockDetector):
            self._backend.set_provider(provider)

    def shutdown(self) -> None:
        try:
            self._backend.shutdown()
        except Exception:
            pass


def _select_backend(cfg, event_bus):
    """Pick the backend from config; returns (backend, is_mock, reason)."""
    from vision.mock_detector import MockDetector  # noqa: PLC0415
    from vision.tflite_backend import TFLiteBackend
    from vision.yolo_backend import YOLOBackend

    choice = cfg.get("vision.backend", "auto")
    classes = list(cfg.get("vision.classes_of_interest", []))
    threshold = float(cfg.get("vision.confidence_threshold", 0.4))

    if choice in ("yolo", "auto"):
        try:
            backend = YOLOBackend(
                model_name=cfg.get("vision.model", "yolov8n"),
                model_path=cfg.get("vision.model_path"),
                conf_threshold=threshold,
                classes=classes,
            )
            return backend, False, None
        except DetectorUnavailable as exc:
            if choice == "yolo":
                # Explicit yolo requested and missing → fall back to mock.
                return MockDetector(), True, str(exc)

    if choice in ("tflite", "auto"):
        try:
            backend = TFLiteBackend(
                model_name=cfg.get("vision.model", "efficientdet_lite0"),
                conf_threshold=threshold,
                classes=classes,
            )
            return backend, False, None
        except DetectorUnavailable as exc:
            if choice == "tflite":
                return MockDetector(), True, str(exc)

    # auto with everything unavailable, or explicit mock
    return MockDetector(), True, "no real detector backend available (auto)"