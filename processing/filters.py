"""
processing/filters.py — Configurable smoothing filters.

Used for distance, velocity, and sensor streams.  Filters are small and
stateless-per-instance; they never buffer more than a bounded window.
"""

from __future__ import annotations

import collections
from typing import Optional


class MovingAverage:
    """Sliding-window arithmetic mean."""

    def __init__(self, window: int = 5) -> None:
        self._window = max(1, int(window))
        self._buf: collections.deque[float] = collections.deque(maxlen=self._window)

    def update(self, value: float) -> float:
        self._buf.append(float(value))
        return sum(self._buf) / len(self._buf)

    def reset(self) -> None:
        self._buf.clear()

    @property
    def size(self) -> int:
        return len(self._buf)


class ExponentialMovingAverage:
    """EMA: value = alpha * new + (1 - alpha) * previous."""

    def __init__(self, alpha: float = 0.4) -> None:
        self._alpha = max(0.0, min(1.0, float(alpha)))
        self._value: Optional[float] = None

    def update(self, value: float) -> float:
        value = float(value)
        if self._value is None:
            self._value = value
        else:
            self._value = self._alpha * value + (1.0 - self._alpha) * self._value
        return self._value

    def reset(self) -> None:
        self._value = None

    @property
    def value(self) -> Optional[float]:
        return self._value


class MedianFilter:
    """Sliding-window median — robust against outliers."""

    def __init__(self, window: int = 5) -> None:
        self._window = max(1, int(window))
        self._buf: collections.deque[float] = collections.deque(maxlen=self._window)

    def update(self, value: float) -> float:
        self._buf.append(float(value))
        return sorted(self._buf)[len(self._buf) // 2]

    def reset(self) -> None:
        self._buf.clear()


class RateLimiter:
    """Time-based gate: allows a new emission at most every *interval_s*."""

    def __init__(self, interval_s: float) -> None:
        self._interval = max(0.0, float(interval_s))
        self._last: float = float("-inf")

    def allow(self, now: float) -> bool:
        if now - self._last >= self._interval:
            self._last = now
            return True
        return False

    def reset(self) -> None:
        self._last = 0.0