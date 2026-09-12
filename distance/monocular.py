"""
distance/monocular.py — Monocular distance estimation (pinhole geometry).

    distance_m = (known_real_width_m × focal_length_px) / bbox_width_px

⚠ This is an ESTIMATE, never ground truth.  Confidence is deliberately
reduced when the estimate is unreliable (uncalibrated camera, truncated
bbox, unstable bbox width, unknown class).
"""

from __future__ import annotations

from typing import Optional

from core.models import Detection, DistanceEstimate
from core.reasons import Reason

EDGE_MARGIN_PX = 5


class MonocularDistanceEstimator:
    def __init__(self, focal_length_px: float = 600.0,
                 known_widths_m: Optional[dict[str, float]] = None,
                 min_distance_m: float = 0.2,
                 max_distance_m: float = 20.0) -> None:
        self._focal = float(focal_length_px)
        self._widths = dict(known_widths_m or {})
        self._min_d = float(min_distance_m)
        self._max_d = float(max_distance_m)

    # ── Public API ────────────────────────────────────────────────────────────

    def estimate(self, detection: Detection,
                 calibration_available: bool,
                 frame_w: int,
                 frame_h: int,
                 prev_width_px: Optional[int] = None) -> DistanceEstimate:
        """Estimate distance for one detection."""
        reasons: list[str] = []
        confidence = 0.9

        width_px = detection.width_px
        if width_px <= 0:
            return DistanceEstimate(None, 0.0, "monocular_geometry", False,
                                    detection.timestamp, Reason.INVALID_BBOX)
        if detection.class_name not in self._widths:
            return DistanceEstimate(None, 0.0, "monocular_geometry", False,
                                    detection.timestamp, "UNKNOWN_CLASS_WIDTH")

        if not calibration_available:
            confidence *= 0.5
            reasons.append(Reason.CALIBRATION_MISSING)

        if self._touches_edge(detection.bbox, frame_w, frame_h):
            confidence *= 0.7
            reasons.append("APPROXIMATE_PARTIAL_VISIBILITY")

        if prev_width_px is not None and prev_width_px > 0:
            delta = abs(width_px - prev_width_px) / prev_width_px
            if delta > 0.35:
                confidence *= 0.8
                reasons.append("BBOX_UNSTABLE")

        raw = (self._widths[detection.class_name] * self._focal) / width_px

        # Clamp to a plausible envelope; out-of-envelope ⇒ approximate.
        if raw < self._min_d or raw > self._max_d:
            raw = max(self._min_d, min(self._max_d, raw))
            confidence *= 0.8
            reasons.append("CLAMPED")

        valid, reason = _validate(raw, self._min_d, self._max_d)
        if not valid:
            return DistanceEstimate(None, 0.0, "monocular_geometry", False,
                                    detection.timestamp, reason)

        return DistanceEstimate(
            distance_m=raw,
            confidence=round(min(1.0, confidence), 3),
            method="monocular_geometry",
            valid=True,
            timestamp=detection.timestamp,
            reason=";".join(reasons) if reasons else None,
        )

    # ── Internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _touches_edge(bbox: tuple[int, int, int, int], frame_w: int,
                      frame_h: int, margin: int = EDGE_MARGIN_PX) -> bool:
        x1, y1, x2, y2 = bbox
        return (x1 <= margin or y1 <= margin
                or x2 >= frame_w - margin or y2 >= frame_h - margin)


def _validate(distance_m: float, low: float, high: float) -> tuple[bool, Optional[str]]:
    if low <= distance_m <= high:
        return True, None
    return False, "OUT_OF_RANGE"