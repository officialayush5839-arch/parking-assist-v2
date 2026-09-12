"""
tracking/iou_tracker.py — Lightweight IOU-based tracker.

Greedy bounding-box-overlap matching between frames (same-class only).
Ported and extended from the v1 ``tinker-vision-alert`` detector smoother:
tracks now carry full lifecycle state and timestamps, and identity is
preserved while a track is temporarily lost.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.models import Detection, TrackedObject, TrackState
from tracking.tracker import ObjectTracker


@dataclass
class _Track:
    track_id: int
    class_name: str
    bbox: tuple[int, int, int, int]
    confidence: float
    first_seen: float
    last_seen: float
    lost_frames: int = 0
    state: TrackState = TrackState.NEW


def _iou(a: tuple[int, int, int, int],
         b: tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


class IOUTracker(ObjectTracker):
    def __init__(self, iou_threshold: float = 0.30,
                 max_lost_frames: int = 20) -> None:
        self._iou_threshold = float(iou_threshold)
        self._max_lost = int(max_lost_frames)
        self._next_id = 1
        self._tracks: list[_Track] = []

    @property
    def name(self) -> str:
        return "iou"

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1

    def update(self, detections: list[Detection],
               timestamp: float) -> list[TrackedObject]:
        matched_det: set[int] = set()
        matched_track: set[int] = set()

        # Greedy matching: each track takes its best same-class IOU match.
        for ti, track in enumerate(self._tracks):
            best_iou, best_di = 0.0, -1
            for di, det in enumerate(detections):
                if di in matched_det or det.class_name != track.class_name:
                    continue
                iou = _iou(track.bbox, det.bbox)
                if iou > best_iou:
                    best_iou, best_di = iou, di
            if best_di >= 0 and best_iou >= self._iou_threshold:
                det = detections[best_di]
                track.bbox = det.bbox
                track.confidence = det.confidence
                track.last_seen = timestamp
                track.lost_frames = 0
                track.state = TrackState.ACTIVE
                matched_det.add(best_di)
                matched_track.add(ti)

        # Unmatched tracks: temporarily lost, then dropped.
        for ti, track in enumerate(self._tracks):
            if ti not in matched_track:
                track.lost_frames += 1
                if track.lost_frames >= self._max_lost:
                    track.state = TrackState.LOST
                elif track.lost_frames > 0:
                    track.state = TrackState.TEMPORARILY_LOST

        self._tracks = [t for t in self._tracks if t.state != TrackState.LOST]

        # New tracks for unmatched detections.
        for di, det in enumerate(detections):
            if di in matched_det:
                continue
            self._tracks.append(_Track(
                track_id=self._next_id,
                class_name=det.class_name,
                bbox=det.bbox,
                confidence=det.confidence,
                first_seen=timestamp,
                last_seen=timestamp,
                state=TrackState.NEW,
            ))
            self._next_id += 1

        return [self._to_tracked(t) for t in self._tracks]

    # ── Internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _to_tracked(t: _Track) -> TrackedObject:
        cx = (t.bbox[0] + t.bbox[2]) / 2.0
        cy = (t.bbox[1] + t.bbox[3]) / 2.0
        return TrackedObject(
            track_id=t.track_id,
            class_name=t.class_name,
            bbox=t.bbox,
            center_x=cx,
            center_y=cy,
            estimated_distance=None,
            velocity=0.0,
            confidence=t.confidence,
            first_seen=t.first_seen,
            last_seen=t.last_seen,
            state=t.state,
        )