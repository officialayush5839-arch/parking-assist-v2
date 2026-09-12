"""
fusion/fusion_policy.py — Transparent fusion policy.

The first implementation is deliberately NOT a learned fusion model:
it is a configurable, explainable policy (validity gating, confidence
weighting, disagreement detection).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FusionPolicy:
    enabled: bool = True
    disagreement_threshold_m: float = 0.75
    conservative_on_disagreement: bool = True
    sensor_trust: float = 0.90        # confidence assigned to a valid ultrasonic
    min_vision_confidence: float = 0.30  # below this, treat vision as unusable
    min_sensor_range_m: float = 0.05
    max_sensor_range_m: float = 4.5
    min_monocular_m: float = 0.2
    max_monocular_m: float = 20.0

    @classmethod
    def from_cfg(cls, cfg) -> "FusionPolicy":
        return cls(
            enabled=bool(cfg.get("fusion.enabled", True)),
            disagreement_threshold_m=float(
                cfg.get("fusion.disagreement_threshold_m", 0.75)),
            conservative_on_disagreement=bool(
                cfg.get("fusion.conservative_on_disagreement", True)),
            sensor_trust=float(cfg.get("fusion.sensor_trust", 0.90)),
            min_sensor_range_m=float(
                cfg.get("distance.ultrasonic.min_range_m", 0.05)),
            max_sensor_range_m=float(
                cfg.get("distance.ultrasonic.max_range_m", 4.5)),
            min_monocular_m=float(
                cfg.get("distance.monocular.min_distance_m", 0.2)),
            max_monocular_m=float(
                cfg.get("distance.monocular.max_distance_m", 20.0)),
        )