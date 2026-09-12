"""
acquisition/frame_reader.py — Frame acquisition wrapper.

Wraps a CameraInterface, adds frame IDs and read statistics, and surfaces
camera health to diagnostics.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from acquisition.timestamp import SequenceCounter, now_wall
from camera.interface import CameraInterface


class FrameReader:
    def __init__(self, camera: CameraInterface) -> None:
        self._camera = camera
        self._seq = SequenceCounter(1)
        self._frames_read = 0
        self._frames_dropped = 0

    @property
    def camera(self) -> CameraInterface:
        return self._camera

    @property
    def healthy(self) -> bool:
        return self._camera.healthy

    @property
    def stats(self) -> dict:
        return {
            "frames_read": self._frames_read,
            "frames_dropped": self._frames_dropped,
        }

    def read(self) -> tuple[Optional[np.ndarray], int, float]:
        """Returns (frame, frame_id, timestamp_wall).  frame=None on failure."""
        frame = self._camera.read()
        if frame is None:
            self._frames_dropped += 1
            return None, self._seq.next(), now_wall()
        self._frames_read += 1
        return frame, self._seq.next(), now_wall()