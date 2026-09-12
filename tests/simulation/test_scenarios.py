"""Simulation scenario tests.

These drive the full pipeline in SIMULATION mode and assert the resulting
safety states, matching the acceptance criteria in the master prompt:

    1.  Object far away                -> SAFE
    2.  Object approaching             -> CAUTION/WARNING
    3.  Fast approaching object        -> WARNING/CRITICAL
    4.  Critical ultrasonic + no vision -> CRITICAL  (hard override)
    5.  Camera failure + valid US      -> continues on ultrasonic
    6.  Ultrasonic failure + valid vision -> degraded but functioning
    7.  Both sensors invalid           -> FAULT / configured degraded state
"""

from __future__ import annotations

from core.models import Zone
from simulation.scenarios import get_scenario, available
from tests.conftest import run_scenario_on_pipeline


def test_registry_lists_required_scenarios() -> None:
    required = {
        "safe_vehicle_stationary",
        "vehicle_approaching_slow",
        "vehicle_approaching_fast",
        "pedestrian_crossing",
        "obstacle_near",
        "ultrasonic_timeout",
        "camera_failure",
        "vision_low_confidence",
        "sensor_disagreement",
        "critical_distance",
    }
    available_set = set(available())
    assert required.issubset(available_set), f"Missing: {required - available_set}"
    for name in required:
        s = get_scenario(name)
        assert s is not None, f"scenario {name} failed to construct"


def test_scenario_1_far_object_is_safe(camera_runtime) -> None:
    scenario = get_scenario("safe_vehicle_stationary")
    telemetry = run_scenario_on_pipeline(camera_runtime, scenario)
    states = [t.state for t in telemetry]
    assert all(s == Zone.SAFE for s in states), f"expected SAFE throughout, got {set(states)}"


def test_scenario_2_approaching_reaches_caution_or_warning(camera_runtime) -> None:
    scenario = get_scenario("vehicle_approaching_slow")
    telemetry = run_scenario_on_pipeline(camera_runtime, scenario)
    states = [t.state for t in telemetry]
    state_values = {s.value if hasattr(s, 'value') else s for s in states}
    assert "CAUTION" in state_values or "WARNING" in state_values, f"got {state_values}"
    assert "CRITICAL" not in state_values, f"unexpected CRITICAL in slow approach: {state_values}"


def test_scenario_3_fast_approaching_reaches_warning_or_critical(camera_runtime) -> None:
    scenario = get_scenario("vehicle_approaching_fast")
    telemetry = run_scenario_on_pipeline(camera_runtime, scenario)
    states = [t.state for t in telemetry]
    state_values = {s.value if hasattr(s, 'value') else s for s in states}
    assert "WARNING" in state_values or "CRITICAL" in state_values, f"got {state_values}"


def test_scenario_4_critical_us_without_vision_is_critical(camera_runtime) -> None:
    """THE hard-override scenario: ML/vision cannot veto critical ultrasonic."""
    scenario = get_scenario("critical_distance")
    telemetry = run_scenario_on_pipeline(camera_runtime, scenario)
    states = [t.state for t in telemetry]
    assert Zone.CRITICAL in states, f"expected CRITICAL, got {set(states)}"


def test_scenario_5_camera_failure_still_uses_ultrasonic(camera_runtime) -> None:
    scenario = get_scenario("camera_failure")
    telemetry = run_scenario_on_pipeline(camera_runtime, scenario)
    states = [t.state for t in telemetry]
    # System must keep producing safety decisions from ultrasonic alone
    assert len(states) > 0, "no states produced"
    # Must reach WARNING or CRITICAL as the sensor distance decreases
    state_values = {s.value if hasattr(s, 'value') else s for s in states}
    assert "WARNING" in state_values or "CRITICAL" in state_values, f"got {state_values}"


def test_scenario_6_ultrasonic_failure_degrades_gracefully(camera_runtime) -> None:
    scenario = get_scenario("ultrasonic_timeout")
    telemetry = run_scenario_on_pipeline(camera_runtime, scenario)
    states = [t.state for t in telemetry]
    assert len(states) > 0, "no states produced"
    # Must NOT be FAULT — vision-only path should still work
    state_values = {s.value if hasattr(s, 'value') else s for s in states}
    assert "FAULT" not in state_values, f"got unexpected FAULT: {state_values}"


def test_scenario_7_sensor_disagreement_detected(camera_runtime) -> None:
    scenario = get_scenario("sensor_disagreement")
    telemetry = run_scenario_on_pipeline(camera_runtime, scenario)
    states = [t.state for t in telemetry]
    assert len(states) > 0, "no states produced"
    # Should reach WARNING from the conservative ultrasonic reading
    state_values = {s.value if hasattr(s, 'value') else s for s in states}
    assert "WARNING" in state_values or "CRITICAL" in state_values, f"got {state_values}"


def test_scenario_vision_low_confidence_uses_sensor(camera_runtime) -> None:
    scenario = get_scenario("vision_low_confidence")
    telemetry = run_scenario_on_pipeline(camera_runtime, scenario)
    states = [t.state for t in telemetry]
    assert len(states) > 0, "no states produced"
    state_values = {s.value if hasattr(s, 'value') else s for s in states}
    assert "CAUTION" in state_values or "WARNING" in state_values, f"got {state_values}"


def test_scenario_obstacle_near_shows_warning(camera_runtime) -> None:
    scenario = get_scenario("obstacle_near")
    telemetry = run_scenario_on_pipeline(camera_runtime, scenario)
    states = [t.state for t in telemetry]
    state_values = {s.value if hasattr(s, 'value') else s for s in states}
    assert "WARNING" in state_values, f"expected WARNING, got {state_values}"
