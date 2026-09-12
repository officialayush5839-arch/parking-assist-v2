"""
vision/preprocessing.py — Vision-side preprocessing.

Wraps the cheap operations from ``camera.preprocessing`` and adds ROI
extraction.  Kept intentionally light for edge hardware.
"""

from __future__ import annotations

import numpy as np

from camera.preprocessing import (
    PreprocessedFrame,
    check_brightness,
    preprocess,
    validate_frame,
)

__all__ = ["PreprocessedFrame", "check_brightness", "preprocess", "validate_frame"]


def extract_roi(frame: np.ndarray, roi: tuple[float, float, float, float]) -> np.ndarray:
    """Extract a ROI as normalised fractions (x0, y0, x1, y1 in 0..1).

    Falls back to the full frame when the ROI is invalid.
    """
    if frame is None or frame.size == 0:
        return frame
    h, w = frame.shape[:2]
    try:
        x0, y0, x1, y1 = (float(v) for v in roi)
    except (TypeError, ValueError):
        return frame
    x0, x1 = int(x0 * w), int(x1 * w)
    y0, y1 = int(y0 * h), int(y1 * h)
    x0, y0 = max(0, min(w, x0)), max(0, min(h, y0))
    x1, y1 = max(x0 + 1, min(w, x1)), max(y0 + 1, min(h, y1))
    return frame[y0:y1, x0:x1]