"""
processing/outliers.py — Spike rejection for time-series measurements.

Safety-critical streams are smoothed but *not* over-filtered: spikes above
a plausibility bound are rejected outright (flagged), while small jitter is
absorbed by the EMA in ``filters.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SpikeResult:
    value: Optional[float]   # accepted value (None when rejected)
    rejected: bool
    reason: str = ""


class SpikeRejector:
    """Reject jumps larger than *max_delta* per update relative to the last
    accepted value.  Useful for closing speed and raw sensor deltas."""

    def __init__(self, max_delta: float = 5.0) -> None:
        self._max_delta = abs(float(max_delta))
        self._last: Optional[float] = None

    def update(self, value: float) -> SpikeResult:
        value = float(value)
        if self._last is None:
            self._last = value
            return SpikeResult(value=value, rejected=False)

        delta = abs(value - self._last)
        if delta > self._max_delta:
            return SpikeResult(
                value=None,
                rejected=True,
                reason=f"spike: |{value:.2f} - {self._last:.2f}| > {self._max_delta:.2f}",
            )
        self._last = value
        return SpikeResult(value=value, rejected=False)

    def reset(self) -> None:
        self._last = None


class HampelFilter:
    """Hampel-style median filter with threshold in median-absolute-deviation
    units.  Values outside the window are replaced by the window median."""

    def __init__(self, window: int = 7, n_sigmas: float = 3.0) -> None:
        self._window = max(3, int(window))
        self._n_sigmas = float(n_sigmas)
        self._buf: list[float] = []

    def update(self, value: float) -> float:
        self._buf.append(float(value))
        if len(self._buf) > self._window:
            self._buf.pop(0)

        if len(self._buf) < self._window:
            return value

        median = sorted(self._buf)[len(self._buf) // 2]
        deviations = sorted(abs(v - median) for v in self._buf)
        mad = deviations[len(deviations) // 2]
        if mad == 0.0:
            return value
        threshold = self._n_sigmas * 1.4826 * mad
        return median if abs(value - median) > threshold else value

    def reset(self) -> None:
        self._buf.clear()