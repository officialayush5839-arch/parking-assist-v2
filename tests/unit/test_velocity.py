"""Velocity estimation: kinematics, smoothing, spike rejection."""

from tracking.velocity import VelocityEstimator


def test_closing_speed_sign_and_magnitude():
    v = VelocityEstimator(ema_alpha=1.0, history_s=10.0)
    assert v.update(1, 2.5, 0.0) is None
    speed = v.update(1, 2.0, 0.5)
    assert speed is not None
    assert abs(speed - 1.0) < 1e-6  # (2.5 - 2.0) / 0.5 = 1.0 m/s approaching


def test_moving_away_is_negative():
    v = VelocityEstimator(ema_alpha=1.0, history_s=10.0)
    v.update(1, 1.0, 0.0)
    speed = v.update(1, 1.5, 0.5)
    assert speed is not None
    assert speed < 0  # receding


def test_ema_smoothing():
    v = VelocityEstimator(ema_alpha=0.5, history_s=10.0)
    v.update(1, 3.0, 0.0)
    s1 = v.update(1, 2.5, 0.5)   # raw 1.0 → smoothed 1.0
    s2 = v.update(1, 2.0, 1.0)   # raw 1.0 → smoothed 1.0
    s3 = v.update(1, 1.0, 1.5)   # raw 2.0 → smoothed 1.5
    assert s1 == s2 == 1.0
    assert abs(s3 - 1.5) < 1e-6


def test_spike_rejected():
    v = VelocityEstimator(ema_alpha=1.0, history_s=10.0, max_plausible_mps=5.0)
    v.update(1, 2.0, 0.0)
    v.update(1, 1.9, 0.1)        # ~1 m/s
    prev = v.update(1, 1.8, 0.2)
    # A wild jump (0.1 m in 0.01 s ⇒ 10 m/s) must be rejected, not applied.
    after = v.update(1, 1.7, 0.21)
    assert abs(after - prev) < 1e-6


def test_remove_resets_track():
    v = VelocityEstimator(history_s=10.0)
    v.update(7, 3.0, 0.0)
    v.update(7, 2.5, 0.5)
    v.remove(7)
    assert v.update(7, 2.0, 1.0) is None