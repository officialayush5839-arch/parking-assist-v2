"""
tracking/tracker.py — Object tracking abstraction.

Tracker implementations maintain persistent object identities across
frames with the lifecycle:

    NEW → ACTIVE ⇄ TEMPORARILY_LOST → LOST → REMOVED

The tracker is backend-swappable (IOU, ByteTrack, future).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.models import Detection, TrackedObject


class ObjectTracker(ABC):
    """Interface for object trackers."""

    @abstractmethod
    def update(self, detections: list[Detection],
               timestamp: float) -> list[TrackedObject]:
        """Match *detections* to existing tracks; return active tracks."""

    @abstractmethod
    def reset(self) -> None:
        """Clear all track state (e.g. after a camera reconnect)."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...