"""
camera/preprocessing.py — Frame validation + cheap preprocessing.

Target hardware is an edge board: only cheap, optional processing is
performed here.  Nothing in this module should be expensive.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class PreprocessedFrame:
    frame: np.ndarray          # processed BGR frame (same size unless resized)
    resized: np.ndarray | None  # network-input-sized array (if resizing requested)
    valid: bool
    low_light: bool
    brightness: float


def validate_frame(frame: Optional[np.ndarray]) -> bool:
    """Cheap sanity checks; returns False for garbage frames."""
    if frame is None:
        return False
    if not isinstance(frame, np.ndarray):
        return False
    if frame.ndim != 3 or frame.shape[2] != 3:
        return False
    if frame.size == 0:
        return False
    return True


def check_brightness(frame: np.ndarray, threshold: int = 40) -> tuple[bool, float]:
    """(is_low_light, mean_brightness).  threshold <= 0 disables."""
    if threshold <= 0:
        return False, 128.0
    try:
        gray = frame.mean(axis=2)
    except Exception:
        return False, 128.0
    brightness = float(gray.mean())
    return brightness < threshold, brightness


def preprocess(frame: np.ndarray,
               target_size: tuple[int, int] | None = None,
               normalize: bool = False,
               denoise: bool = False,
               low_light_threshold: int = 40) -> PreprocessedFrame:
    """Validate and optionally resize/normalize/denoise a frame.

    *target_size* is (width, height) — the detector input size.  The
    returned ``frame`` is always the original-size BGR frame; ``resized``
    is the network-ready array when a target size is given.
    """
    if not validate_frame(frame):
        return PreprocessedFrame(frame, None, False, False, 0.0)

    low_light, brightness = check_brightness(frame, low_light_threshold)

    if denoise:
        try:
            import cv2  # type: ignore  # noqa: PLC0415

            frame = cv2.fastNlMeansDenoisingColored(frame, None, 5, 5, 7, 21)
        except Exception:
            pass

    resized: Optional[np.ndarray] = None
    if target_size is not None:
        w, h = target_size
        try:
            import cv2  # type: ignore  # noqa: PLC0415

            resized = cv2.resize(frame, (w, h))
        except Exception:
            resized = None
        if resized is not None and normalize:
            resized = resized.astype(np.float32) / 255.0

    return PreprocessedFrame(frame, resized, True, low_light, brightness)