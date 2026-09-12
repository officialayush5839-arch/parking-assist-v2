"""
simulation/scenarios/registry.py — Built-in scenarios.

Every scenario is deterministic (time-parameterised) so the simulation
tests are reproducible.  Expected states are listed in the order they
appear as the scenario progresses (used by tests/simulation).
"""

from __future__ import annotations

import math

from simulation.scenario import (
    SCENARIOS,
    Scenario,
    constant,
    get_scenario,  # noqa: F401  (re-exported)
    invalid_after,
    linear,
    make_scenario,
    register,
    sensor_to_vision,
)


def _crossing_center(t: float) -> float:
    """Pedestrian walking across the field of view (x fraction 0.2..0.8)."""
    return 0.5 + 0.3 * math.sin(t * 0.6)


# ── 1. Safe, stationary vehicle ───────────────────────────────────────────────
register(make_scenario(
    "safe_vehicle_stationary",
    "A vehicle stands still ~4 m away.  Expected: SAFE.",
    duration_s=6.0,
    sensor=constant(4.0),
    vision=sensor_to_vision(constant(4.0)),
    expected=["SAFE"],
))

# ── 2. Slow approach ──────────────────────────────────────────────────────────
register(make_scenario(
    "vehicle_approaching_slow",
    "A vehicle approaches slowly (≈0.2 m/s).  Expected: SAFE→CAUTION→WARNING.",
    duration_s=12.0,
    sensor=linear(3.2, 0.8, 0.0, 12.0),
    vision=sensor_to_vision(linear(3.2, 0.8, 0.0, 12.0)),
    expected=["SAFE", "CAUTION", "WARNING"],
))

# ── 3. Fast approach ──────────────────────────────────────────────────────────
register(make_scenario(
    "vehicle_approaching_fast",
    "A vehicle approaches quickly (≈0.35 m/s) into the critical zone.  "
    "Expected: SAFE→CAUTION→WARNING→CRITICAL.",
    duration_s=8.0,
    sensor=linear(3.0, 0.2, 0.0, 8.0),
    vision=sensor_to_vision(linear(3.0, 0.2, 0.0, 8.0)),
    expected=["SAFE", "CAUTION", "WARNING", "CRITICAL"],
))

# ── 4. Pedestrian crossing ────────────────────────────────────────────────────
register(make_scenario(
    "pedestrian_crossing",
    "A pedestrian crosses the field of view (lateral movement).  "
    "Expected: CAUTION/WARNING depending on closest point.",
    duration_s=10.0,
    sensor=linear(2.4, 1.2, 0.0, 5.0),   # approaches, then
    vision=lambda t: 2.4 - 1.2 * min(1.0, max(0.0, t / 5.0)),
    center_frac_x=_crossing_center,
    obj_width_m=0.5,
    vision_confidence=lambda t: 0.85,
    expected=["CAUTION", "WARNING"],
    notes="Vision tracks a person-sized object; ultrasonic sees the closest point.",
))

# ── 5. Static obstacle near ───────────────────────────────────────────────────
register(make_scenario(
    "obstacle_near",
    "A static obstacle at 0.8 m.  Expected: WARNING.",
    duration_s=5.0,
    sensor=constant(0.8),
    vision=sensor_to_vision(constant(0.8)),
    expected=["WARNING"],
))

# ── 6. Ultrasonic timeout, vision healthy ─────────────────────────────────────
register(make_scenario(
    "ultrasonic_timeout",
    "Ultrasonic drops out at t=1 s; vision keeps working.  "
    "Expected: degraded CAUTION/WARNING from vision alone.",
    duration_s=8.0,
    sensor=invalid_after(1.0),
    vision=lambda t: 3.0 - 1.8 * min(1.0, max(0.0, t / 8.0)),
    vision_confidence=lambda t: 0.80,
    expected=["CAUTION", "WARNING"],
    notes="Pipeline must continue with reduced confidence (DEGRADED_MODE).",
))

# ── 7. Camera failure, ultrasonic healthy ─────────────────────────────────────
def _camera_ok_until(t_fail: float) -> object:
    def fn(t: float) -> bool:
        return t < t_fail

    return fn


register(make_scenario(
    "camera_failure",
    "Camera fails at t=3 s; ultrasonic keeps working.  "
    "Expected: safety continues on ultrasonic alone (WARNING/CRITICAL).",
    duration_s=8.0,
    sensor=linear(3.0, 0.6, 0.0, 8.0),
    vision=sensor_to_vision(linear(3.0, 0.6, 0.0, 8.0)),
    camera_healthy=_camera_ok_until(3.0),
    expected=["CAUTION", "WARNING", "CRITICAL"],
    notes="Ultrasonic-only safety path must not depend on the camera.",
))

# ── 8. Vision low confidence ──────────────────────────────────────────────────
register(make_scenario(
    "vision_low_confidence",
    "Vision detects but at confidence below the fusion minimum; "
    "ultrasonic valid.  Expected: sensor-driven CAUTION/WARNING.",
    duration_s=8.0,
    sensor=linear(2.6, 0.9, 0.0, 8.0),
    vision=sensor_to_vision(linear(2.6, 0.9, 0.0, 8.0)),
    vision_confidence=lambda t: 0.20,
    expected=["CAUTION", "WARNING"],
    notes="Low vision confidence must not poison the fusion result.",
))

# ── 9. Sensor / vision disagreement ───────────────────────────────────────────
register(make_scenario(
    "sensor_disagreement",
    "Ultrasonic says 0.9 m but vision says 4.0 m.  "
    "Expected: SENSOR_DISAGREEMENT; conservative policy uses 0.9 m → WARNING.",
    duration_s=5.0,
    sensor=constant(0.9),
    vision=lambda t: 4.0,
    vision_confidence=lambda t: 0.90,
    expected=["WARNING"],
    notes="Measurements are never blindly averaged.",
))

# ── 10. Critical ultrasonic distance, no vision ───────────────────────────────
register(make_scenario(
    "critical_distance",
    "Ultrasonic reports 0.3 m with NO vision detection at all.  "
    "Expected: CRITICAL immediately (hard safety override).",
    duration_s=4.0,
    sensor=constant(0.3),
    vision=lambda t: None,
    expected=["CRITICAL"],
    notes="THE hard-override scenario: ML/vision cannot veto this.",
))


# ── 11. Demo sequence (honest, scripted showcase) ───────────────────────────
def _demo_distance(t: float) -> tuple[float, bool]:
    """Piecewise approach: 4.0 m SAFE → CRITICAL, held at the end."""
    if t < 4:
        return 4.0, True
    if t < 10:
        return 4.0 - 0.33 * (t - 4), True
    if t < 16:
        return 2.0 - 0.13 * (t - 10), True
    if t < 22:
        return 1.2 - 0.11 * (t - 16), True
    if t < 26:
        return 0.55 - 0.05 * (t - 22), True
    return 0.35, True


register(make_scenario(
    "demo_sequence",
    "Scripted showcase: SAFE → vehicle detected → approach → CAUTION → "
    "WARNING → CRITICAL (held).  Used by --mode demo.",
    duration_s=30.0,
    sensor=_demo_distance,
    vision=_demo_distance,
    expected=["SAFE", "CAUTION", "WARNING", "CRITICAL"],
))


def available() -> list[str]:
    return sorted(SCENARIOS)