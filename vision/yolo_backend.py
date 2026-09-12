"""
vision/yolo_backend.py — YOLO-family detection backend (ultralytics).

Weights are **never downloaded automatically** by the pipeline: if the
configured ``.pt`` file is absent the backend raises DetectorUnavailable
and the wrapper falls back to the MockDetector.  Fetch weights with
``tools/fetch_yolo_weights.py`` (see models/README.md).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from core.config import PROJECT_ROOT
from core.errors import DetectorUnavailable
from core.models import Detection
from vision.detector import DetectorBackend

WEIGHTS_DIR = PROJECT_ROOT / "models" / "detector"


class YOLOBackend(DetectorBackend):
    def __init__(self, model_name: str = "yolov8n",
                 model_path: Optional[str] = None,
                 conf_threshold: float = 0.40,
                 classes: Optional[list[str]] = None) -> None:
        self._model_name = model_name
        self._conf = float(conf_threshold)
        self._classes = set(classes or [])
        self._weights = self._find_weights(model_name, model_path)
        self._model = None
        self._names: dict[int, str] = {}

    @property
    def name(self) -> str:
        return f"yolo:{self._model_name}"

    # ── DetectorBackend ───────────────────────────────────────────────────────

    def initialize(self) -> None:
        if self._weights is None:
            raise DetectorUnavailable(
                f"No YOLO weights for {self._model_name!r}. Put a .pt file in "
                f"{WEIGHTS_DIR} (see models/README.md), or set vision.model_path."
            )
        try:
            from ultralytics import YOLO  # type: ignore
        except ImportError as exc:
            raise DetectorUnavailable(
                "ultralytics is not installed (pip install ultralytics)"
            ) from exc
        try:
            self._model = YOLO(str(self._weights))
            self._names = self._model.names if hasattr(self._model, "names") else {}
        except Exception as exc:
            raise DetectorUnavailable(f"Failed to load YOLO model: {exc}") from exc

    def detect(self, frame: np.ndarray, timestamp: float,
               frame_id: int) -> list[Detection]:
        if self._model is None:
            return []
        results = self._model(frame, verbose=False, conf=self._conf)
        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            boxes = result.boxes.xyxy.cpu().numpy()
            scores = result.boxes.conf.cpu().numpy()
            class_ids = result.boxes.cls.cpu().numpy().astype(int)
            for bbox, score, cls_id in zip(boxes, scores, class_ids):
                class_name = self._names.get(int(cls_id), f"class_{cls_id}")
                if self._classes and class_name not in self._classes:
                    continue
                x1, y1, x2, y2 = (int(v) for v in bbox)
                if x2 <= x1 or y2 <= y1:
                    continue
                detections.append(Detection(
                    class_name=class_name,
                    confidence=float(score),
                    bbox=(x1, y1, x2, y2),
                    timestamp=timestamp,
                    frame_id=frame_id,
                ))
        return detections

    def shutdown(self) -> None:
        self._model = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _find_weights(model_name: str,
                      model_path: Optional[str]) -> Optional[Path]:
        if model_path:
            p = Path(model_path)
            return p if p.is_file() else None
        for candidate in (
            WEIGHTS_DIR / f"{model_name}.pt",
            WEIGHTS_DIR / f"{model_name}",
        ):
            if candidate.is_file():
                return candidate
        # Loose search for any .pt in the weights dir.
        if WEIGHTS_DIR.is_dir():
            for f in WEIGHTS_DIR.glob("*.pt"):
                return f
        return None