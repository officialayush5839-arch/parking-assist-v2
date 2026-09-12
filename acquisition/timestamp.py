"""
acquisition/timestamp.py — Timestamping helpers.

Every measurement carries an explicit wall-clock timestamp; ordering is
never inferred from arrival.  Monotonic time is used for rate/latency
measurement, wall time for logs and replay.
"""

from __future__ import annotations

import itertools
import time


def now_wall() -> float:
    """Wall-clock Unix timestamp (seconds)."""
    return time.time()


def now_monotonic() -> float:
    """Monotonic seconds (rate/latency measurement only)."""
    return time.monotonic()


def new_sequence() -> int:
    """Next value from a process-wide sequence counter."""
    return next(_SEQUENCES)


_SEQUENCES = itertools.count(1)


class SequenceCounter:
    """Independent monotonic counter (e.g. per-subsystem frame IDs)."""

    def __init__(self, start: int = 0) -> None:
        self._counter = itertools.count(start)

    def next(self) -> int:
        return next(self._counter)