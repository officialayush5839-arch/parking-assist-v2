"""
fusion/confidence_fusion.py — Sensor/vision fusion.

Transparent strategy per the spec:

    sensor valid + vision valid + agreement good  → weighted fusion
    sensor valid + vision invalid                 → ultrasonic only
    sensor invalid + vision valid                 → monocular only (reduced confidence)
    both invalid                                  → UNKNOWN (valid=False)

Sensor disagreement is detected explicitly — measurements are never
blindly averaged.  With the conservative policy, the closer valid
measurement wins on disagreement.
"""

from __future__ import annotations

from typing import Optional

from core.models import DistanceEstimate, FusionResult, SensorReading
from core.reasons import Reason
from fusion.fusion_policy import FusionPolicy


class ConfidenceFusion:
    def __init__(self, policy: Optional[FusionPolicy] = None) -> None:
        self._policy = policy or FusionPolicy()

    # ── Public API ────────────────────────────────────────────────────────────

    def fuse(self, sensor: Optional[SensorReading],
             vision: Optional[DistanceEstimate],
             now: float) -> FusionResult:
        """Fuse one sensor reading with one vision estimate."""
        sensor_valid = bool(sensor is not None and sensor.valid
                            and sensor.distance_m is not None)
        vision_valid = bool(vision is not None and vision.valid
                            and vision.distance_m is not None
                            and vision.confidence >= self._policy.min_vision_confidence)

        sensor_dist = sensor.distance_m if sensor_valid else None
        vision_dist = vision.distance_m if vision_valid else None
        reasons: list[str] = []
        disagreement = False
        agreement: Optional[float] = None
        method = "none"
        confidence = 0.0
        fused: Optional[float] = None

        if sensor_valid and vision_valid:
            delta = abs(sensor_dist - vision_dist)
            denominator = max(sensor_dist, vision_dist, 1e-6)
            agreement = round(1.0 - min(1.0, delta / denominator), 3)
            disagreement = delta > self._policy.disagreement_threshold_m

            if disagreement:
                reasons.append(Reason.SENSOR_DISAGREEMENT)
                if self._policy.conservative_on_disagreement:
                    # Safety bias: the closer valid measurement governs.
                    fused = min(sensor_dist, vision_dist)
                    method = "conservative_min"
                    confidence = min(1.0, self._policy.sensor_trust
                                     + vision.confidence) / 2.0
                else:
                    fused = (sensor_dist + vision_dist) / 2.0
                    method = "weighted"
                    confidence = (self._policy.sensor_trust + vision.confidence) / 2.0
            else:
                w_s = self._policy.sensor_trust
                w_v = vision.confidence
                fused = (w_s * sensor_dist + w_v * vision_dist) / (w_s + w_v)
                method = "weighted"
                confidence = round(min(1.0, (w_s + w_v) / 2.0), 3)

        elif sensor_valid:
            fused = sensor_dist
            method = "ultrasonic_only"
            confidence = self._policy.sensor_trust
            reasons.append(Reason.LOW_VISION_CONFIDENCE)

        elif vision_valid:
            fused = vision_dist
            method = "monocular_only"
            confidence = round(min(1.0, vision.confidence * 0.8), 3)
            reasons.append(Reason.LOW_SENSOR_CONFIDENCE)

        else:
            method = "none"
            confidence = 0.0
            reasons.append(Reason.NO_VALID_DISTANCE)

        return FusionResult(
            fused_distance_m=fused,
            confidence=confidence,
            method=method,
            valid=fused is not None,
            timestamp=now,
            vision_distance=vision_dist,
            sensor_distance=sensor_dist,
            agreement=agreement,
            disagreement=disagreement,
            sensor_valid=sensor_valid,
            vision_valid=vision_valid,
            reason_codes=reasons,
        )