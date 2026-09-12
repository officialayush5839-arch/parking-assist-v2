"""
ml/ttc.py — Deterministic kinematic time-to-collision.

    TTC = distance / closing_speed      (distance > 0, closing_speed > 0)
    TTC = infinity                      (no approach path / stationary)

TTC is pure kinematics; it feeds the deterministic safety engine and the
advisory risk score.  It is *never* a learned prediction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class TTCResult:
    ttc_seconds: Optional[float]   # math.inf ⇒ no collision path
    valid: bool
    distance_m: Optional[float]
    closing_speed_mps: Optional[float]
    method: str = "deterministic_kinematic"


def compute_ttc(distance_m: Optional[float],
                closing_speed_mps: Optional[float]) -> TTCResult:
    """Compute TTC from distance and closing speed (positive = approaching)."""
    if distance_m is None or distance_m <= 0.0:
        return TTCResult(None, False, distance_m, closing_speed_mps)
    if closing_speed_mps is None or closing_speed_mps <= 0.0:
        # No closing motion ⇒ no collision path.
        return TTCResult(math.inf, True, distance_m, closing_speed_mps)
    ttc = distance_m / closing_speed_mps
    return TTCResult(ttc, True, distance_m, closing_speed_mps)


def ttc_display(ttc: Optional[float]) -> str:
    """Human-readable TTC for LCD / console (e.g. '2.19s', '∞', '-' )."""
    if ttc is None:
        return "-"
    if math.isinf(ttc):
        return "inf"
    return f"{ttc:.2f}s"