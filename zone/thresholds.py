"""
zone/thresholds.py — Deterministic zone thresholds.

Thresholds come from configuration (config/safety.yaml) and are
DEMO / INITIAL values that MUST be re-validated for any real deployment.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.models import Zone


@dataclass(frozen=True)
class ZoneThresholds:
    safe_min_m: float = 2.5
    caution_min_m: float = 1.8
    warning_min_m: float = 1.0
    critical_min_m: float = 0.5

    def __post_init__(self) -> None:
        if not (self.safe_min_m > self.caution_min_m > self.warning_min_m > self.critical_min_m > 0):
            raise ValueError(
                "Thresholds must satisfy safe > caution > warning > critical > 0: "
                f"{self}"
            )

    @classmethod
    def from_cfg(cls, cfg) -> "ZoneThresholds":
        zones = cfg.get("safety.zones", {})
        return cls(
            safe_min_m=float(zones.get("safe_min_m", 2.5)),
            caution_min_m=float(zones.get("caution_min_m", 1.8)),
            warning_min_m=float(zones.get("warning_min_m", 1.0)),
            critical_min_m=float(zones.get("critical_min_m", 0.5)),
        )

    def classify(self, distance_m: float) -> Zone:
        """Map a distance (metres) to a zone.  Distances below the critical
        threshold are CRITICAL — this is the hard-safety boundary."""
        if distance_m < self.critical_min_m:
            return Zone.CRITICAL
        if distance_m < self.warning_min_m:
            return Zone.WARNING
        if distance_m < self.caution_min_m:
            return Zone.CAUTION
        return Zone.SAFE

    def as_dict(self) -> dict:
        return {
            "safe_min_m": self.safe_min_m,
            "caution_min_m": self.caution_min_m,
            "warning_min_m": self.warning_min_m,
            "critical_min_m": self.critical_min_m,
        }