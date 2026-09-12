"""Filters: moving average, EMA, median, rate limiter."""

from processing.filters import (
    ExponentialMovingAverage,
    MedianFilter,
    MovingAverage,
    RateLimiter,
)


def test_moving_average():
    f = MovingAverage(window=3)
    assert f.update(1.0) == 1.0
    assert f.update(2.0) == 1.5
    assert f.update(3.0) == 2.0
    # Window slides
    assert f.update(100.0) == 35.0


def test_ema():
    f = ExponentialMovingAverage(alpha=0.5)
    assert f.update(10.0) == 10.0
    assert f.update(20.0) == 15.0
    assert f.update(30.0) == 22.5


def test_ema_reset():
    f = ExponentialMovingAverage(alpha=0.5)
    f.update(10.0)
    f.reset()
    assert f.update(100.0) == 100.0


def test_median_filter():
    f = MedianFilter(window=5)
    for v in (1, 2, 100, 3, 4):
        f.update(v)
    # Window now (2, 100, 3, 4, 5) → sorted (2,3,4,5,100) → median 4.
    assert f.update(5) == 4


def test_rate_limiter():
    r = RateLimiter(interval_s=1.0)
    assert r.allow(0.0)
    assert not r.allow(0.5)
    assert r.allow(1.1)