"""
camera/video_camera.py — Video-file camera backend.

Reads frames from a recorded video file (e.g. a Tinker Board capture).
Loops the file when it ends unless ``loop=False``.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from camera.interface import CameraInterface


class VideoFileCamera(CameraInterface):
    def __init__(self, path: str | Path, loop: bool = False,
                 target_fps: int = 15) -> None:
        self._path = str(path)
        self._loop = loop
        self._min_interval = 1.0 / max(1, target_fps)
        self._cap: Optional[object] = None
        self._last_grab = 0.0
        self._alive = False
        self._finished = False

    @property
    def healthy(self) -> bool:
        return self._alive

    def start(self) -> None:
        import cv2  # type: ignore  # noqa: PLC0415

        if self._cap is not None:
            return
        self._cap = cv2.VideoCapture(self._path)
        self._alive = bool(self._cap and self._cap.isOpened())

    def read(self) -> Optional[object]:
        import cv2  # type: ignore  # noqa: PLC0415

        now = time.monotonic()
        wait = self._min_interval - (now - self._last_grab)
        if wait > 0:
            time.sleep(wait)

        if self._cap is None:
            self.start()
        if self._cap is None:
            return None

        ok, frame = self._cap.read()
        if ok and frame is not None:
            self._alive = True
            self._last_grab = time.monotonic()
            return frame

        if self._loop:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._cap.read()
            if ok and frame is not None:
                return frame
        self._finished = True
        self._alive = False
        return None

    def stop(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        self._alive = False

    def get_resolution(self) -> tuple[int, int]:
        import cv2  # type: ignore  # noqa: PLC0415

        if self._cap is not None:
            w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if w > 0 and h > 0:
                return (w, h)
        return (640, 480)

    @property
    def finished(self) -> bool:
        return self._finished