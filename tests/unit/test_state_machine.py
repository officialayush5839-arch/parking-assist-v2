"""Deterministic safety state machine."""

from core.models import Zone
from zone.state_machine import SafetyStateMachine


def test_escalation_is_immediate():
    sm = SafetyStateMachine(stability_frames=3)
    assert sm.update(Zone.SAFE).state == Zone.SAFE
    result = sm.update(Zone.WARNING)   # escalation ⇒ immediate
    assert result.changed
    assert result.state == Zone.WARNING


def test_critical_immediate():
    sm = SafetyStateMachine(stability_frames=3)
    sm.update(Zone.SAFE)
    result = sm.update(Zone.CRITICAL)
    assert result.changed
    assert result.state == Zone.CRITICAL


def test_fault_immediate():
    sm = SafetyStateMachine(stability_frames=3)
    sm.update(Zone.SAFE)
    result = sm.update(Zone.FAULT)
    assert result.changed
    assert result.state == Zone.FAULT


def test_recovery_requires_stability():
    sm = SafetyStateMachine(stability_frames=3)
    sm.update(Zone.CRITICAL)
    # First recovery candidate is not committed yet.
    assert sm.update(Zone.SAFE).state == Zone.CRITICAL
    assert sm.update(Zone.SAFE).state == Zone.CRITICAL
    result = sm.update(Zone.SAFE)   # 3rd consecutive
    assert result.changed
    assert result.state == Zone.SAFE


def test_recovery_flicker_does_not_commit():
    sm = SafetyStateMachine(stability_frames=3)
    sm.update(Zone.CRITICAL)
    sm.update(Zone.SAFE)
    sm.update(Zone.CRITICAL)   # interruption resets the recovery count
    sm.update(Zone.SAFE)
    assert sm.update(Zone.SAFE).state == Zone.CRITICAL  # only 2 consecutive