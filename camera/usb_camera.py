"""
camera/usb_camera.py — USB webcam backend.

OpenCV VideoCapture with automatic reconnect and a target frame rate.
Ported from the v1 ``tinker-vision-alert`` CameraStream and adapted to the
CameraInterface.
"""

from __future__ import annotations

import time
from typing import Optional

from camera.interface import CameraInterface


class USBCamera(CameraInterface):
    def __init__(self, source: str | int = 0, width: int = 640,
                 height: int = 480, target_fps: int = 15,
                 reconnect_attempts: int = 3,
                 reconnect_delay_s: float = 0.5) -> None:
        if isinstance(source, str) and source.isdigit():
            source = int(source)
        self._source = source
        self._width = width
        self._height = height
        self._min_interval = 1.0 / max(1, target_fps)
        self._reconnect_attempts = max(1, reconnect_attempts)
        self._reconnect_delay = reconnect_delay_s
        self._cap: Optional[object] = None
        self._last_grab = 0.0
        self._alive = False

    # ── CameraInterface ───────────────────────────────────────────────────────

    @property
    def healthy(self) -> bool:
        return self._alive

    def start(self) -> None:
        import cv2  # type: ignore  # noqa: PLC0415

        if self._cap is not None:
            return
        self._cap = cv2.VideoCapture(self._source)
        try:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        except Exception:
            pass
        if not self._cap.isOpened():
            self._cap = None
            self._alive = False
            return
        time.sleep(0.25)  # let auto-exposure settle
        self._alive = True

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

        # Fault: try to reconnect.
        self._alive = False
        self._release()
        for _ in range(self._reconnect_attempts):
            time.sleep(self._reconnect_delay)
            self.start()
            if self._cap is not None:
                ok, frame = self._cap.read()
                if ok and frame is not None:
                    self._alive = True
                    self._last_grab = time.monotonic()
                    return frame
                self._release()
        return None

    def stop(self) -> None:
        self._release()
        self._alive = False

    def get_resolution(self) -> tuple[int, int]:
        return (self._width, self._height)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _release(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None