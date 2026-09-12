"""
tracking/velocity.py — Closing-speed estimation.

Uses timestamped distance history per track:

    closing_speed = (distance_prev - distance_now) / dt     [m/s, +ve = approaching]

Applies EMA smoothing and rejects implausible spikes.  Distance history is
bounded to ``history_s`` seconds to keep memory flat.
"""

from __future__ import annotations

import collections
from typing import Optional

from processing.outliers import SpikeRejector


class VelocityEstimator:
    def __init__(self, ema_alpha: float = 0.4,
                 max_plausible_mps: float = 5.0,
                 history_s: float = 3.0,
                 min_dt_s: float = 0.05) -> None:
        self._alpha = ema_alpha
        self._max_speed = abs(max_plausible_mps)
        self._history_s = float(history_s)
        self._min_dt = float(min_dt_s)
        self._history: dict[int, collections.deque] = {}
        self._smoothed: dict[int, float] = {}
        self._spike: dict[int, SpikeRejector] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, track_id: int, distance_m: Optional[float],
               timestamp: float) -> Optional[float]:
        """Update one track's distance sample; returns smoothed closing
        speed (m/s, positive = approaching) or None when not computable."""
        if distance_m is None or distance_m <= 0:
            return self._smoothed.get(track_id)

        hist = self._history.setdefault(track_id, collections.deque())
        # Prune old samples.
        cutoff = timestamp - self._history_s
        while hist and hist[0][0] < cutoff:
            hist.popleft()
        hist.append((timestamp, float(distance_m)))

        if len(hist) < 2:
            return self._smoothed.get(track_id)

        (t0, d0), (t1, d1) = hist[-2], hist[-1]
        dt = t1 - t0
        if dt < self._min_dt:
            return self._smoothed.get(track_id)

        raw_speed = (d0 - d1) / dt  # positive when approaching
        if abs(raw_speed) > self._max_speed:
            return self._smoothed.get(track_id)

        # Spike rejection against the previous smoothed value.
        prev = self._smoothed.get(track_id)
        if prev is not None:
            rejector = self._spike.setdefault(track_id, SpikeRejector(self._max_speed))
            result = rejector.update(raw_speed)
            if result.rejected:
                return prev

        if prev is None:
            smoothed = raw_speed
        else:
            smoothed = self._alpha * raw_speed + (1.0 - self._alpha) * prev
        self._smoothed[track_id] = smoothed
        return smoothed

    def remove(self, track_id: int) -> None:
        self._history.pop(track_id, None)
        self._smoothed.pop(track_id, None)
        self._spike.pop(track_id, None)

    def reset(self) -> None:
        self._history.clear()
        self._smoothed.clear()
        self._spike.clear()