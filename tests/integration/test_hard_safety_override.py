"""
Integration test: HARD SAFETY OVERRIDE through the full pipeline.

Given:
    ultrasonic_distance = 0.30 m
    critical_threshold  = 0.50 m
    vision_detection    = NONE
    ML risk             = LOW

Then:
    final_state MUST equal CRITICAL

This proves the AI/ML (and vision/tracking) can never veto a hard
safety condition.
"""

import time

from core.models import RiskAssessment, RiskClass, Zone

from tests.conftest import run_scenario_on_pipeline


def test_pipeline_hard_override_ultrasonic_only(camera_runtime):
    """Direct pipeline drive: critical ultrasonic, no vision, LOW ML risk."""
    rt = camera_runtime

    # No vision detections ever.
    rt.detector.set_mock_provider(lambda now: None)
    # Sensor pinned at 0.30 m (valid) — below the 0.50 m critical threshold.
    rt.sensor.set_provider(lambda now: (0.30, True))
    rt.pipeline.reset()

    final_states = []
    for i in range(10):
        reading = rt.sensor_reader.read()
        tel = rt.pipeline.step(
            frame=None, frame_id=i, frame_ts=float(i),
            sensor_reading=reading, camera_healthy=True,
            predictor_note="deterministic_ttc")
        final_states.append(tel.state)

    # ML risk is LOW by construction of the deterministic predictor at
    # these features, and vision is absent — yet the state MUST be CRITICAL.
    assert final_states[-1] == Zone.CRITICAL
    assert Zone.CRITICAL in final_states


def test_pipeline_hard_override_with_high_ml_risk(camera_runtime):
    """Even when the ML risk reports HIGH, the deterministic decision
    must remain CRITICAL — but the ML reason may be attached."""
    rt = camera_runtime
    rt.detector.set_mock_provider(lambda now: None)
    rt.sensor.set_provider(lambda now: (0.30, True))
    rt.pipeline.reset()

    # Force a HIGH-risk assessment through a stub predictor.
    class HighRiskPredictor:
        def name(self):
            return "ml"

        def predict(self, features):
            return RiskAssessment(0.99, RiskClass.HIGH, 0.9, "ml", time.time())

    rt.pipeline.predictor = HighRiskPredictor()

    states = []
    for i in range(5):
        reading = rt.sensor_reader.read()
        tel = rt.pipeline.step(frame=None, frame_id=i, frame_ts=float(i),
                               sensor_reading=reading, camera_healthy=True,
                               predictor_note="ml")
        states.append(tel.state)
    assert states[-1] == Zone.CRITICAL


def test_pipeline_critical_distance_scenario(camera_runtime):
    """The 'critical_distance' scenario drives the same rule end-to-end."""
    from simulation.scenarios import get_scenario

    scenario = get_scenario("critical_distance")
    telemetry = run_scenario_on_pipeline(camera_runtime, scenario)
    states = [t.state for t in telemetry]
    assert Zone.CRITICAL in states
    assert states[-1] == Zone.CRITICAL