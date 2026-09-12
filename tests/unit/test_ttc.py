"""Deterministic kinematic TTC."""

import math

from ml.ttc import compute_ttc, ttc_display


def test_ttc_basic():
    result = compute_ttc(2.0, 1.0)
    assert result.valid
    assert result.ttc_seconds == 2.0


def test_ttc_no_closing_speed_is_infinite():
    result = compute_ttc(2.0, 0.0)
    assert result.valid
    assert math.isinf(result.ttc_seconds)


def test_ttc_negative_speed_is_infinite():
    # Moving away ⇒ no collision path
    result = compute_ttc(2.0, -0.5)
    assert result.valid
    assert math.isinf(result.ttc_seconds)


def test_ttc_invalid_distance():
    result = compute_ttc(None, 1.0)
    assert not result.valid
    assert result.ttc_seconds is None
    assert compute_ttc(0.0, 1.0).ttc_seconds is None


def test_ttc_display():
    assert ttc_display(2.19) == "2.19s"
    assert ttc_display(float("inf")) == "inf"
    assert ttc_display(None) == "-"