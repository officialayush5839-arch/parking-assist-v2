"""
vision/tflite_backend.py — TFLite detection backend.

Ported from the v1 ``tinker-vision-alert`` detector (EfficientDet-Lite0/1/2,
MobileNet-SSD v2).  Requires ``tflite-runtime`` (or full ``tensorflow``)
plus a downloaded model in ``models/detector/<model_name>/`` — see
``tools/fetch_tflite_model.py`` / models/README.md.  When the runtime or
weights are unavailable the backend raises DetectorUnavailable and the
wrapper falls back to mock.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from core.config import PROJECT_ROOT
from core.errors import DetectorUnavailable
from core.models import Detection
from vision.detector import DetectorBackend

MODEL_ROOT = PROJECT_ROOT / "models" / "detector"

COCO_LABELS_FALLBACK = [
    "???", "person", "bicycle", "car", "motorcycle", "airplane", "bus",
    "train", "truck", "boat", "traffic light", "fire hydrant", "???",
    "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse",
    "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "???",
    "backpack", "umbrella", "???", "???", "handbag", "tie", "suitcase",
    "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat",
    "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle",
    "???", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana",
    "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza",
    "donut", "cake", "chair", "couch", "potted plant", "bed", "???",
    "dining table", "???", "???", "toilet", "???", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster",
    "sink", "refrigerator", "???", "book", "clock", "vase", "scissors",
    "teddy bear", "hair drier", "toothbrush",
]


class TFLiteBackend(DetectorBackend):
    def __init__(self, model_name: str = "efficientdet_lite0",
                 conf_threshold: float = 0.40,
                 classes: Optional[list[str]] = None) -> None:
        self._model_name = model_name
        self._conf = float(conf_threshold)
        self._classes = set(classes or [])
        self._interpreter = None
        self._labels: list[str] = []
        self._model_w = 0
        self._model_h = 0
        self._uint8_input = False
        self._input_index = None
        self._output_indices: list[int] = []

    @property
    def name(self) -> str:
        return f"tflite:{self._model_name}"

    # ── DetectorBackend ───────────────────────────────────────────────────────

    def initialize(self) -> None:
        try:
            from tflite_runtime.interpreter import Interpreter  # type: ignore
        except ImportError:
            try:
                from tensorflow.lite.python.interpreter import Interpreter  # type: ignore  # noqa: PLC0415
            except ImportError as exc:
                raise DetectorUnavailable(
                    "Neither tflite-runtime nor tensorflow is installed "
                    "(pip install tflite-runtime)"
                ) from exc

        tflite_path = self._find_model()
        if tflite_path is None:
            raise DetectorUnavailable(
                f"No .tflite model for {self._model_name!r} in {MODEL_ROOT}. "
                "Run tools/fetch_tflite_model.py (see models/README.md)."
            )
        self._labels = self._load_labels(self._model_name)

        self._interpreter = Interpreter(model_path=str(tflite_path))
        self._interpreter.allocate_tensors()
        input_details = self._interpreter.get_input_details()
        output_details = self._interpreter.get_output_details()
        shape = input_details[0]["shape"]
        self._model_h, self._model_w = int(shape[1]), int(shape[2])
        self._uint8_input = input_details[0]["dtype"] == np.uint8
        self._input_index = input_details[0]["index"]
        self._output_indices = [o["index"] for o in output_details[:3]]

    def detect(self, frame: np.ndarray, timestamp: float,
               frame_id: int) -> list[Detection]:
        if self._interpreter is None:
            return []
        import cv2  # type: ignore  # noqa: PLC0415

        frame_h, frame_w = frame.shape[:2]
        resized = cv2.resize(frame, (self._model_w, self._model_h))
        if self._uint8_input:
            input_data = np.expand_dims(resized, axis=0).astype(np.uint8)
        else:
            input_data = np.expand_dims(resized, axis=0).astype(np.float32) / 255.0

        self._interpreter.set_tensor(self._input_index, input_data)
        self._interpreter.invoke()
        boxes = self._interpreter.get_tensor(self._output_indices[0])[0]
        classes = self._interpreter.get_tensor(self._output_indices[1])[0]
        scores = self._interpreter.get_tensor(self._output_indices[2])[0]

        detections: list[Detection] = []
        for i in range(len(scores)):
            score = float(scores[i])
            if score < self._conf:
                continue
            cls_id = int(classes[i])
            label = self._labels[cls_id] if cls_id < len(self._labels) else f"class_{cls_id}"
            if self._classes and label not in self._classes:
                continue
            ymin, xmin, ymax, xmax = boxes[i]
            bbox = (
                max(0, int(xmin * frame_w)),
                max(0, int(ymin * frame_h)),
                min(frame_w, int(xmax * frame_w)),
                min(frame_h, int(ymax * frame_h)),
            )
            if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
                continue
            detections.append(Detection(label, score, bbox, timestamp, frame_id))
        return detections

    def shutdown(self) -> None:
        self._interpreter = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_model(self) -> Optional[Path]:
        model_dir = MODEL_ROOT / self._model_name
        if model_dir.is_dir():
            for f in model_dir.iterdir():
                if f.suffix == ".tflite":
                    return f
        for f in MODEL_ROOT.glob("*.tflite"):
            return f
        return None

    def _load_labels(self, model_name: str) -> list[str]:
        model_dir = MODEL_ROOT / model_name
        if model_dir.is_dir():
            for f in model_dir.iterdir():
                if f.suffix == ".txt":
                    return [line.strip() for line in f.read_text(encoding="utf-8").splitlines()]
        return COCO_LABELS_FALLBACK