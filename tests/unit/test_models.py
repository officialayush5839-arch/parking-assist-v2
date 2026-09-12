"""Data-model serialization round-trips."""

import math

from core.models import (
    Detection,
    SafetyDecision,
    SensorReading,
    Telemetry,
    Zone,
    to_jsonable,
)


def test_detection_center():
    d = Detection("car", 0.9, (10, 20, 110, 120), 1.0, 1)
    cx, cy = d.center
    assert cx == 60.0
    assert cy == 70.0
    assert d.width_px == 100


def test_safety_decision_jsonable():
    d = SafetyDecision(
        state=Zone.WARNING, distance_m=0.92, closing_speed_mps=0.42,
        ttc_seconds=2.19, risk_score=0.72, confidence=0.88,
        reason_codes=["DISTANCE_WARNING"], timestamp=123.0, sources=["ultrasonic"])
    j = d.jsonable
    assert j["state"] == "WARNING"
    assert j["reason_codes"] == ["DISTANCE_WARNING"]


def test_inf_converted_to_none():
    t = Telemetry(
        cycle_id=1, timestamp=1.0, state=Zone.SAFE, distance_m=2.0,
        confidence=0.9, object_class="car", closing_speed_mps=0.0,
        ttc_seconds=math.inf, risk_score=0.1, fps=10.0, latency_ms=5.0,
        detections=1, tracks=1)
    j = to_jsonable(t)
    assert j["ttc_seconds"] is None


def test_sensor_reading_round_trip():
    r = SensorReading("ultrasonic", 1.42, True, 123.0, 7)
    j = to_jsonable(r)
    assert j["distance_m"] == 1.42
    assert j["sequence"] == 7