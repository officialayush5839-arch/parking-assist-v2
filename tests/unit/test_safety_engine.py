"""Deterministic safety engine — including the hard-safety override."""

import time

from core.events import EventBus, EventType
from core.models import DistanceEstimate, RiskAssessment, RiskClass, SensorReading, Zone
from core.reasons import Reason
from zone.safety_engine import DeterministicSafetyEngine
from zone.thresholds import ZoneThresholds

THRESHOLDS = ZoneThresholds(safe_min_m=2.5, caution_min_m=1.8,
                            warning_min_m=1.0, critical_min_m=0.5)
CONFIG = {
    "safety": {"hard_safety_enabled": True, "stability_frames": 3,
               "no_distance_state": "FAULT", "degraded_confidence": 0.40,
               "high_closing_speed_mps": 1.0, "ttc_warning_s": 3.0,
               "ttc_critical_s": 1.5},
}


def _sensor(distance, valid=True):
    return SensorReading("ultrasonic", distance if valid else None, valid, time.time())


def _vision(distance, valid=True, confidence=0.8):
    return DistanceEstimate(distance if valid else None, confidence,
                            "monocular_geometry", valid, time.time())


def _risk(score=0.0, risk_class=RiskClass.LOW):
    return RiskAssessment(score, risk_class, 0.8, "deterministic_ttc", time.time())


def test_hard_safety_override_critical():
    """The acceptance rule: ultrasonic 0.30 m with critical 0.50 m and NO
    vision and LOW ML risk MUST produce CRITICAL."""
    engine = DeterministicSafetyEngine(THRESHOLDS, CONFIG)
    decision = engine.evaluate(
        fusion=None, sensor=_sensor(0.30), vision=None, risk=_risk(0.0, RiskClass.LOW),
        closing_speed_mps=None, now=time.time())
    assert decision.state == Zone.CRITICAL
    assert Reason.HARD_SENSOR_LIMIT in decision.reason_codes
    assert decision.distance_m == 0.30


def test_ai_cannot_veto_hard_safety():
    """Even with ML risk LOW, vision absent, tracker lost, a critical
    ultrasonic reading stays CRITICAL."""
    engine = DeterministicSafetyEngine(THRESHOLDS, CONFIG)
    decision = engine.evaluate(
        fusion=None, sensor=_sensor(0.30), vision=None,
        risk=_risk(0.0, RiskClass.LOW), closing_speed_mps=None, now=time.time())
    assert decision.state == Zone.CRITICAL


def test_fault_when_both_sources_invalid():
    engine = DeterministicSafetyEngine(THRESHOLDS, CONFIG)
    decision = engine.evaluate(
        fusion=None, sensor=_sensor(None, valid=False),
        vision=_vision(None, valid=False), risk=_risk(), closing_speed_mps=None,
        now=time.time())
    assert decision.state == Zone.FAULT
    assert Reason.NO_VALID_DISTANCE in decision.reason_codes


def test_sensor_only_degraded():
    engine = DeterministicSafetyEngine(THRESHOLDS, CONFIG)
    decision = engine.evaluate(
        fusion=None, sensor=_sensor(0.9), vision=None, risk=_risk(),
        closing_speed_mps=None, now=time.time())
    assert decision.state == Zone.WARNING
    assert decision.confidence == CONFIG["safety"]["degraded_confidence"]


def test_vision_only_degraded():
    engine = DeterministicSafetyEngine(THRESHOLDS, CONFIG)
    decision = engine.evaluate(
        fusion=None, sensor=_sensor(None, valid=False), vision=_vision(1.5),
        risk=_risk(), closing_speed_mps=None, now=time.time())
    assert decision.state == Zone.CAUTION


def test_ml_risk_is_advisory_only():
    """HIGH ML risk adds a reason code but never changes the state."""
    engine = DeterministicSafetyEngine(THRESHOLDS, CONFIG)
    decision = engine.evaluate(
        fusion=None, sensor=_sensor(4.0), vision=_vision(4.0),
        risk=_risk(0.95, RiskClass.HIGH), closing_speed_mps=0.0, now=time.time())
    assert decision.state == Zone.SAFE
    assert Reason.ML_RISK_HIGH in decision.reason_codes


def test_high_closing_speed_escalates_caution_to_warning():
    engine = DeterministicSafetyEngine(THRESHOLDS, CONFIG)
    # 1.7 m is in CAUTION zone (>= 1.0, < 1.8); high closing speed escalates to WARNING
    # TTC = 1.7/1.1 = 1.55s > 1.5s so no TTC escalation to CRITICAL
    decision = engine.evaluate(
        fusion=None, sensor=_sensor(1.7), vision=None,
        risk=_risk(), closing_speed_mps=1.1, now=time.time())
    assert decision.state == Zone.WARNING
    assert Reason.HIGH_CLOSING_SPEED in decision.reason_codes


def test_ttc_critical_escalates_to_critical():
    engine = DeterministicSafetyEngine(THRESHOLDS, CONFIG)
    # distance 1.2 m, speed 1.5 m/s ⇒ TTC 0.8 s ≤ 1.5 s ⇒ CRITICAL
    decision = engine.evaluate(
        fusion=None, sensor=_sensor(1.2), vision=None,
        risk=_risk(), closing_speed_mps=1.5, now=time.time())
    assert decision.state == Zone.CRITICAL
    assert Reason.TTC_CRITICAL in decision.reason_codes


def test_fusion_disagreement_reason_flows_through():
    from fusion.confidence_fusion import ConfidenceFusion
    from fusion.fusion_policy import FusionPolicy

    fusion = ConfidenceFusion(FusionPolicy())
    fused = fusion.fuse(_sensor(0.9), _vision(4.0), time.time())
    engine = DeterministicSafetyEngine(THRESHOLDS, CONFIG)
    decision = engine.evaluate(fusion=fused, sensor=_sensor(0.9),
                               vision=_vision(4.0), risk=_risk(),
                               closing_speed_mps=0.0, now=time.time())
    assert Reason.SENSOR_DISAGREEMENT in decision.reason_codes
    # Conservative policy ⇒ fused uses the closer measurement ⇒ WARNING.
    assert decision.state == Zone.WARNING


def test_state_change_event_published():
    bus = EventBus()
    seen = []
    bus.subscribe(lambda e: seen.append(e.event_type))
    engine = DeterministicSafetyEngine(THRESHOLDS, CONFIG, event_bus=bus)
    engine.evaluate(fusion=None, sensor=_sensor(0.3), vision=None, risk=None,
                    closing_speed_mps=None, now=time.time())
    assert EventType.SAFETY_STATE_CHANGED in seen
    assert EventType.CRITICAL_ALERT in seen