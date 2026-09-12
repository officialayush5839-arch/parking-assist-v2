"""
camera/interface.py — Camera interface.

All camera backends (USB, MIPI/CSI, video file, mock/synthetic) implement
this interface.  ``read()`` never raises: it returns None while the
camera is unavailable, and ``healthy`` reports connectivity.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np


class CameraInterface(ABC):
    @abstractmethod
    def start(self) -> None:
        """Open the camera; must be safe to call repeatedly."""

    @abstractmethod
    def read(self) -> Optional[np.ndarray]:
        """Return one BGR frame, or None when unavailable."""

    @abstractmethod
    def stop(self) -> None:
        """Release the camera."""

    @abstractmethod
    def get_resolution(self) -> tuple[int, int]:
        """(width, height) of the delivered frames."""

    @property
    @abstractmethod
    def healthy(self) -> bool:
        """True when the most recent read succeeded / is expected to."""

    @property
    def name(self) -> str:
        return self.__class__.__name__