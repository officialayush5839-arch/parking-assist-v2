"""
processing/validation.py — Range and timestamp validation.

Pure functions: no I/O, no state.  Used by the distance validator, the
ultrasonic reader, and the safety engine.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationResult:
    valid: bool
    reason: Optional[str] = None


def validate_range(value: Optional[float], low: float, high: float) -> ValidationResult:
    """Check *value* is finite and within [low, high]."""
    if value is None:
        return ValidationResult(False, "MISSING")
    try:
        if not (low <= float(value) <= high):
            return ValidationResult(False, "OUT_OF_RANGE")
    except (TypeError, ValueError):
        return ValidationResult(False, "NON_NUMERIC")
    return ValidationResult(True, None)


def validate_timestamp(ts: Optional[float], now: Optional[float] = None,
                       max_age_s: float = 5.0) -> ValidationResult:
    """Check a timestamp is present and not stale by more than *max_age_s*."""
    if ts is None:
        return ValidationResult(False, "MISSING_TIMESTAMP")
    if ts <= 0:
        return ValidationResult(False, "INVALID_TIMESTAMP")
    if now is None:
        now = time.time()
    if now - ts > max_age_s:
        return ValidationResult(False, "STALE_TIMESTAMP")
    return ValidationResult(True, None)


def validate_positive(value: Optional[float], max_value: float) -> ValidationResult:
    return validate_range(value, 0.0, max_value)