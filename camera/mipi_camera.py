"""
camera/mipi_camera.py — MIPI CSI camera backend (Tinker Board).

On the Tinker Board the CSI camera is exposed as a V4L2 device
(e.g. ``/dev/video0``).  This backend is a thin, explicitly-named wrapper
around the same OpenCV capture path as USBCamera, so configuration can
declare ``backend: mipi`` without code changes.
"""

from __future__ import annotations

from camera.usb_camera import USBCamera


class MIPICamera(USBCamera):
    """MIPI/CSI camera via V4L2.  Use source='/dev/videoN'."""

    def __init__(self, source: str | int = "/dev/video0", width: int = 640,
                 height: int = 480, target_fps: int = 15,
                 reconnect_attempts: int = 3,
                 reconnect_delay_s: float = 0.5) -> None:
        super().__init__(source=source, width=width, height=height,
                         target_fps=target_fps,
                         reconnect_attempts=reconnect_attempts,
                         reconnect_delay_s=reconnect_delay_s)

    @property
    def name(self) -> str:
        return "mipi_camera"