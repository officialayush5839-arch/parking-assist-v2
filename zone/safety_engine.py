"""
zone/safety_engine.py — Deterministic safety engine.

Decision hierarchy (highest authority first):

    1. Sensor health
    2. HARD safety limits          ← valid ultrasonic ≤ critical ⇒ CRITICAL,
                                     regardless of vision/ML output
    3. Sensor + vision fusion
    4. Kinematic escalation (closing speed / TTC)
    5. ML risk (advisory ONLY — never changes state)
    6. Deterministic state machine (hysteresis)

The AI/ML never overrides a hard safety condition.  This module encodes
that rule explicitly.
"""

from __future__ import annotations

import math
from typing import Optional

from core.events import EventBus, EventType, Severity
from core.models import (
    DistanceEstimate,
    FusionResult,
    RiskAssessment,
    SafetyDecision,
    SensorReading,
    Zone,
)
from core.reasons import Reason
from ml.ttc import compute_ttc
from zone.state_machine import SafetyStateMachine
from zone.thresholds import ZoneThresholds


class DeterministicSafetyEngine:
    def __init__(self, thresholds: ZoneThresholds, cfg=None,
                 event_bus: Optional[EventBus] = None) -> None:
        self._thresholds = thresholds
        self._hard_safety = bool(_cfg_get(cfg, "safety.hard_safety_enabled", True))
        self._no_distance_state = _parse_zone(
            _cfg_get(cfg, "safety.no_distance_state", "FAULT"), Zone.FAULT
        )
        self._degraded_confidence = float(_cfg_get(cfg, "safety.degraded_confidence", 0.40))
        self._high_speed = float(_cfg_get(cfg, "safety.high_closing_speed_mps", 1.0))
        self._ttc_warning = float(_cfg_get(cfg, "safety.ttc_warning_s", 3.0))
        self._ttc_critical = float(_cfg_get(cfg, "safety.ttc_critical_s", 1.5))
        stability = int(_cfg_get(cfg, "safety.stability_frames", 3))

        self._sm = SafetyStateMachine(stability_frames=stability)
        self._bus = event_bus

    # ── Public API ────────────────────────────────────────────────────────────

    def evaluate(self,
                 fusion: Optional[FusionResult],
                 sensor: Optional[SensorReading],
                 vision: Optional[DistanceEstimate],
                 risk: Optional[RiskAssessment],
                 closing_speed_mps: Optional[float],
                 now: float) -> SafetyDecision:
        """Produce the deterministic safety decision for one cycle."""
        reasons: list[str] = []
        sources: list[str] = []
        distance: Optional[float] = None
        confidence = 0.0
        candidate: Zone

        sensor_valid = bool(sensor is not None and sensor.valid
                            and sensor.distance_m is not None)
        vision_valid = bool(vision is not None and vision.valid
                            and vision.distance_m is not None)

        # ── 1. HARD SAFETY OVERRIDE ─────────────────────────────────────────
        # A valid ultrasonic reading at/below the critical threshold forces
        # CRITICAL even when the camera sees nothing, the tracker lost the
        # object, and the ML model reports LOW risk.
        hard_override = (
            self._hard_safety
            and sensor_valid
            and sensor.distance_m <= self._thresholds.critical_min_m
        )

        if hard_override:
            distance = float(sensor.distance_m)
            candidate = Zone.CRITICAL
            confidence = 1.0
            sources = ["ultrasonic"]
            reasons = [Reason.DISTANCE_CRITICAL, Reason.HARD_SENSOR_LIMIT]
        else:
            # ── 2. Fusion / fallback distance sources ───────────────────────
            if fusion is not None and fusion.valid and fusion.fused_distance_m is not None:
                distance = float(fusion.fused_distance_m)
                confidence = fusion.confidence
                reasons += list(fusion.reason_codes)
                sources = _sources_from_method(fusion.method)
            elif sensor_valid:
                distance = float(sensor.distance_m)
                confidence = self._degraded_confidence
                sources = ["ultrasonic"]
                reasons = [Reason.DEGRADED_MODE, Reason.LOW_VISION_CONFIDENCE]
            elif vision_valid:
                distance = float(vision.distance_m)
                confidence = min(1.0, vision.confidence * self._degraded_confidence * 2.0)
                sources = ["vision"]
                reasons = [Reason.DEGRADED_MODE, Reason.LOW_SENSOR_CONFIDENCE]
            else:
                distance = None
                confidence = 0.0
                reasons = [Reason.NO_VALID_DISTANCE, Reason.FAULT_DETECTED]
                candidate = self._no_distance_state
                self._maybe_publish(EventType.FAULT_DETECTED, Severity.ERROR,
                                    "safety", {"reason": "no valid distance source"})
                return self._finish(candidate, distance, closing_speed_mps, None,
                                    risk, confidence, reasons, sources, now)

            # ── 3. Zone from distance ───────────────────────────────────────
            candidate = self._thresholds.classify(distance)
            if candidate == Zone.CRITICAL:
                reasons.append(Reason.DISTANCE_CRITICAL)
            elif candidate == Zone.WARNING:
                reasons.append(Reason.DISTANCE_WARNING)
            elif candidate == Zone.CAUTION:
                reasons.append(Reason.DISTANCE_CAUTION)

            # ── 4. Deterministic kinematic escalation ───────────────────────
            ttc = compute_ttc(distance, closing_speed_mps).ttc_seconds
            if closing_speed_mps is not None and closing_speed_mps >= self._high_speed:
                reasons.append(Reason.HIGH_CLOSING_SPEED)
                reasons.append(Reason.OBJECT_APPROACHING)
                if candidate == Zone.CAUTION:
                    candidate = Zone.WARNING
            if ttc is not None and math.isfinite(ttc):
                if ttc <= self._ttc_critical:
                    candidate = Zone.CRITICAL
                    reasons.append(Reason.TTC_CRITICAL)
                elif ttc <= self._ttc_warning:
                    if candidate.severity < Zone.WARNING.severity:
                        candidate = Zone.WARNING
                    reasons.append(Reason.TTC_WARNING)
            return self._finish(candidate, distance, closing_speed_mps, ttc,
                                risk, confidence, reasons, sources, now)

        # hard override path
        ttc = compute_ttc(distance, closing_speed_mps).ttc_seconds
        return self._finish(candidate, distance, closing_speed_mps, ttc,
                            risk, confidence, reasons, sources, now)

    @property
    def state(self) -> Zone:
        return self._sm.state

    def reset(self) -> None:
        self._sm.reset()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _finish(self, candidate: Zone, distance: Optional[float],
                closing_speed: Optional[float], ttc: Optional[float],
                risk: Optional[RiskAssessment], confidence: float,
                reasons: list[str], sources: list[str], now: float) -> SafetyDecision:
        # ML risk is advisory only — attach the reason, never the authority.
        if risk is not None and risk.risk_class.value == "HIGH":
            reasons.append(Reason.ML_RISK_HIGH)

        update = self._sm.update(candidate)
        if update.changed:
            self._maybe_publish(
                EventType.SAFETY_STATE_CHANGED, Severity.INFO, "safety",
                {"from": update.from_state.value, "to": update.state.value,
                 "distance_m": distance, "reason_codes": reasons},
            )
        if update.state == Zone.CRITICAL:
            self._maybe_publish(EventType.CRITICAL_ALERT, Severity.CRITICAL,
                                "safety", {"distance_m": distance, "ttc_seconds": ttc})
        if update.state == Zone.FAULT:
            self._maybe_publish(EventType.FAULT_DETECTED, Severity.ERROR,
                                "safety", {"reason_codes": reasons})

        return SafetyDecision(
            state=update.state,
            distance_m=distance,
            closing_speed_mps=closing_speed,
            ttc_seconds=ttc,
            risk_score=risk.risk_score if risk is not None else None,
            confidence=min(1.0, max(0.0, confidence)),
            reason_codes=_dedupe(reasons),
            timestamp=now,
            sources=sources,
        )

    def _maybe_publish(self, event_type: EventType, severity: Severity,
                       source: str, payload: dict) -> None:
        if self._bus is not None:
            self._bus.publish(event_type, severity, source, payload)


def _cfg_get(cfg, dotted: str, default):
    """Read a dotted path from a Settings object or a plain dict."""
    if cfg is None:
        return default
    if hasattr(cfg, "get"):
        return cfg.get(dotted, default)
    cur = cfg
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def _parse_zone(name: str, default: Zone) -> Zone:
    try:
        return Zone(name.upper())
    except ValueError:
        return default


def _sources_from_method(method: str) -> list[str]:
    if method in ("weighted", "ultrasonic_and_vision"):
        return ["ultrasonic", "vision"]
    if method == "ultrasonic_only":
        return ["ultrasonic"]
    if method == "monocular_only":
        return ["vision"]
    return []


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        value = item.value if isinstance(item, Reason) else str(item)
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out