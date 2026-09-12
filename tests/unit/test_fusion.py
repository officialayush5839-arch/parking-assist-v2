"""Sensor/vision fusion: validity gating, weighting, disagreement."""

import time

from core.models import DistanceEstimate, SensorReading
from fusion.confidence_fusion import ConfidenceFusion
from fusion.fusion_policy import FusionPolicy
from core.reasons import Reason


def _sensor(distance, valid=True, source="ultrasonic"):
    return SensorReading(source, distance if valid else None, valid, time.time())


def _vision(distance, confidence=0.8, valid=True):
    return DistanceEstimate(distance if valid else None, confidence,
                            "monocular_geometry", valid, time.time())


def test_both_valid_weighted():
    fusion = ConfidenceFusion(FusionPolicy())
    result = fusion.fuse(_sensor(1.30), _vision(1.42, 0.8), time.time())
    assert result.valid
    assert result.method == "weighted"
    assert result.fused_distance_m is not None
    assert 1.30 <= result.fused_distance_m <= 1.42
    assert result.agreement is not None and result.agreement > 0.9
    assert not result.disagreement


def test_sensor_only():
    fusion = ConfidenceFusion(FusionPolicy())
    result = fusion.fuse(_sensor(0.9), None, time.time())
    assert result.valid
    assert result.method == "ultrasonic_only"
    assert result.fused_distance_m == 0.9
    assert Reason.LOW_VISION_CONFIDENCE in result.reason_codes


def test_vision_only_reduced_confidence():
    fusion = ConfidenceFusion(FusionPolicy(sensor_trust=0.9))
    result = fusion.fuse(None, _vision(2.1, 0.8), time.time())
    assert result.valid
    assert result.method == "monocular_only"
    assert abs(result.confidence - 0.8 * 0.8) < 1e-6


def test_both_invalid():
    fusion = ConfidenceFusion(FusionPolicy())
    result = fusion.fuse(_sensor(None, valid=False), _vision(None, valid=False), time.time())
    assert not result.valid
    assert result.method == "none"


def test_vision_below_min_confidence_treated_invalid():
    fusion = ConfidenceFusion(FusionPolicy(min_vision_confidence=0.30))
    result = fusion.fuse(_sensor(1.0), _vision(2.0, 0.20), time.time())
    assert result.method == "ultrasonic_only"


def test_disagreement_detected():
    fusion = ConfidenceFusion(FusionPolicy(disagreement_threshold_m=0.75))
    result = fusion.fuse(_sensor(0.8), _vision(4.5), time.time())
    assert result.disagreement
    assert Reason.SENSOR_DISAGREEMENT in result.reason_codes


def test_disagreement_conservative_uses_min():
    fusion = ConfidenceFusion(FusionPolicy(disagreement_threshold_m=0.75,
                                           conservative_on_disagreement=True))
    result = fusion.fuse(_sensor(0.8), _vision(4.5), time.time())
    assert result.fused_distance_m == 0.8  # closer (safer) measurement wins


def test_disagreement_not_blindly_averaged():
    # With the conservative policy OFF, disagreement averages — but the
    # default policy is conservative, and this proves the two policies
    # differ (measurements are never silently merged either way).
    fusion = ConfidenceFusion(FusionPolicy(disagreement_threshold_m=0.75,
                                           conservative_on_disagreement=False))
    result = fusion.fuse(_sensor(0.8), _vision(4.5), time.time())
    assert result.fused_distance_m == (0.8 + 4.5) / 2.0
    assert result.disagreement