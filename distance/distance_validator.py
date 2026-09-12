"""
distance/distance_validator.py — Validation for distance measurements.

Applied to both the physical ultrasonic stream and monocular estimates
before they enter fusion.  Pure functions — no I/O.
"""

from __future__ import annotations

from typing import Optional

from processing.validation import validate_range, validate_timestamp

REASON_OUT_OF_RANGE = "OUT_OF_RANGE"
REASON_TIMEOUT = "TIMEOUT"
REASON_INVALID = "INVALID"
REASON_MISSING = "MISSING"
REASON_STALE = "STALE"
REASON_OK = None


def validate_ultrasonic(distance_m: Optional[float],
                        min_range_m: float,
                        max_range_m: float,
                        timestamp: Optional[float] = None,
                        now: Optional[float] = None,
                        max_age_s: float = 2.0) -> tuple[bool, Optional[str]]:
    """Validate a raw ultrasonic distance + timestamp.

    Returns (valid, reason).  ``reason`` is one of the REASON_* constants
    or None when valid.
    """
    if distance_m is None:
        return False, REASON_MISSING
    range_ok = validate_range(distance_m, min_range_m, max_range_m)
    if not range_ok.valid:
        return False, range_ok.reason  # OUT_OF_RANGE / NON_NUMERIC
    if timestamp is not None:
        ts_ok = validate_timestamp(timestamp, now=now, max_age_s=max_age_s)
        if not ts_ok.valid:
            return False, REASON_STALE
    return True, REASON_OK


def validate_monocular(distance_m: Optional[float],
                       min_distance_m: float,
                       max_distance_m: float) -> tuple[bool, Optional[str]]:
    if distance_m is None:
        return False, REASON_MISSING
    result = validate_range(distance_m, min_distance_m, max_distance_m)
    if not result.valid:
        return False, result.reason
    return True, REASON_OK