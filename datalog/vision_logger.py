"""
datalog/vision_logger.py — Detection + tracking logging (JSONL).

Records detections, tracks, and monocular distance estimates with full
timestamps and frame IDs so sessions can be replayed (tools/replay_log.py).
"""

from __future__ import annotations

from pathlib import Path

from core.models import Detection, DistanceEstimate, TrackedObject, to_jsonable
from datalog.base import RotatingJSONLWriter


class VisionLogger:
    def __init__(self, directory: str | Path,
                 rotate_bytes: int = 10_485_760,
                 rotate_backups: int = 3) -> None:
        self._writer = RotatingJSONLWriter(directory, "vision",
                                           rotate_bytes, rotate_backups)

    def log_detections(self, detections: list[Detection]) -> None:
        self._writer.write({
            "type": "detections",
            "timestamp": detections[0].timestamp if detections else 0.0,
            "count": len(detections),
            "detections": [to_jsonable(d) for d in detections],
        })

    def log_tracks(self, tracks: list[TrackedObject]) -> None:
        if not tracks:
            return
        self._writer.write({
            "type": "tracks",
            "timestamp": tracks[0].last_seen,
            "tracks": [to_jsonable(t) for t in tracks],
        })

    def log_monocular(self, estimate: DistanceEstimate) -> None:
        self._writer.write({
            "type": "monocular",
            **to_jsonable(estimate),
        })

    def close(self) -> None:
        self._writer.close()