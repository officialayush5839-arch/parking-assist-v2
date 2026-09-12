"""
ml/risk_prediction.py — Advisory risk scoring.

The ML risk model is **advisory only**.  Its output flows into the
deterministic safety engine and can never activate safety hardware or
override a hard safety condition.

Backends
--------
* DeterministicTTCPredictor — transparent kinematic risk from distance,
  closing speed, and TTC (the default; no training required).
* MLRiskPredictor          — trained model (joblib/sklearn); raises
  PredictorUnavailable when the model file is missing.
* MockRiskPredictor        — clearly-marked fake for development.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from core.errors import PredictorUnavailable
from core.models import RiskAssessment, RiskClass, to_jsonable


@dataclass
class RiskFeatures:
    """Feature vector for risk prediction (documented order for ML)."""

    distance_m: Optional[float] = None
    closing_speed_mps: Optional[float] = None
    ttc_seconds: Optional[float] = None
    acceleration_mps2: Optional[float] = None
    detector_confidence: Optional[float] = None
    tracker_confidence: Optional[float] = None
    sensor_confidence: Optional[float] = None
    disagreement: bool = False
    class_name: Optional[str] = None
    historical: list[float] = field(default_factory=list)

    # Order used by the ML backend when building a feature row.
    ML_FEATURE_NAMES = [
        "distance_m", "closing_speed_mps", "ttc_seconds", "acceleration_mps2",
        "detector_confidence", "tracker_confidence", "sensor_confidence",
        "disagreement",
    ]

    def ml_row(self) -> list[float]:
        """Feature row in the exact order the ML model was trained on."""
        return [
            self.distance_m if self.distance_m is not None else -1.0,
            self.closing_speed_mps if self.closing_speed_mps is not None else 0.0,
            self.ttc_seconds if self.ttc_seconds is not None and math.isfinite(self.ttc_seconds) else -1.0,
            self.acceleration_mps2 if self.acceleration_mps2 is not None else 0.0,
            self.detector_confidence if self.detector_confidence is not None else 0.0,
            self.tracker_confidence if self.tracker_confidence is not None else 0.0,
            self.sensor_confidence if self.sensor_confidence is not None else 0.0,
            1.0 if self.disagreement else 0.0,
        ]


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


class RiskPredictor(ABC):
    """Interface for risk backends."""

    @abstractmethod
    def predict(self, features: RiskFeatures) -> RiskAssessment:
        ...

    @abstractmethod
    def name(self) -> str:
        ...


class DeterministicTTCPredictor(RiskPredictor):
    """Transparent kinematic risk score.

    risk = 0.5·distance_factor + 0.3·speed_factor + 0.2·ttc_factor
    """

    def __init__(self, safe_min_m: float = 2.5, high_speed_mps: float = 1.0,
                 ttc_warning_s: float = 3.0) -> None:
        self._safe_min = float(safe_min_m)
        self._high_speed = float(high_speed_mps)
        self._ttc_warning = float(ttc_warning_s)

    def name(self) -> str:
        return "deterministic_ttc"

    def predict(self, features: RiskFeatures) -> RiskAssessment:
        distance = features.distance_m
        speed = features.closing_speed_mps or 0.0
        ttc = features.ttc_seconds

        if distance is None or distance <= 0:
            distance_factor = 1.0
        else:
            distance_factor = _clamp01(1.0 - distance / self._safe_min)

        speed_factor = _clamp01(speed / self._high_speed) if self._high_speed > 0 else 0.0

        if ttc is not None and math.isfinite(ttc) and self._ttc_warning > 0:
            ttc_factor = _clamp01((self._ttc_warning - ttc) / self._ttc_warning)
        else:
            ttc_factor = 0.0

        score = _clamp01(0.5 * distance_factor + 0.3 * speed_factor + 0.2 * ttc_factor)
        risk_class = _classify(score)

        confidences = [
            c for c in (features.detector_confidence, features.tracker_confidence,
                        features.sensor_confidence) if c is not None
        ]
        confidence = sum(confidences) / len(confidences) if confidences else 0.8

        return RiskAssessment(
            risk_score=score,
            risk_class=risk_class,
            confidence=confidence,
            method=self.name(),
            timestamp=0.0,
            features=to_jsonable(features),
        )


class MockRiskPredictor(RiskPredictor):
    """Clearly-marked fake predictor (always LOW risk, method='mock')."""

    def name(self) -> str:
        return "mock"

    def predict(self, features: RiskFeatures) -> RiskAssessment:
        return RiskAssessment(
            risk_score=0.0,
            risk_class=RiskClass.LOW,
            confidence=0.0,
            method="mock",
            timestamp=0.0,
            features={"note": "MOCK — no learned model", **to_jsonable(features)},
        )


class MLRiskPredictor(RiskPredictor):
    """Trained sklearn/joblib risk model.

    The model file is expected to contain either a classifier with
    ``predict_proba`` (classes LOW, MEDIUM, HIGH) or a regressor whose
    output is a risk score in [0, 1].
    """

    def __init__(self, model_path: str, safe_min_m: float = 2.5) -> None:
        self._safe_min = float(safe_min_m)
        try:
            import joblib  # type: ignore
        except ImportError as exc:
            raise PredictorUnavailable("joblib is required for ML risk models") from exc
        try:
            self._model = joblib.load(model_path)
        except Exception as exc:
            raise PredictorUnavailable(f"cannot load ML risk model {model_path!r}: {exc}") from exc
        self._path = model_path
        self._is_classifier = hasattr(self._model, "predict_proba")

    def name(self) -> str:
        return "ml"

    def predict(self, features: RiskFeatures) -> RiskAssessment:
        row = [features.ml_row()]
        try:
            if self._is_classifier:
                proba = self._model.predict_proba(row)[0]
                classes = list(self._model.classes_)
                risk_class = classes[int(proba.argmax())]
                score = float(max(proba))
                confidence = score
            else:
                raw = float(self._model.predict(row)[0])
                score = _clamp01(raw)
                risk_class = _classify(score)
                confidence = 0.8
        except Exception as exc:
            raise PredictorUnavailable(f"ML risk inference failed: {exc}") from exc

        return RiskAssessment(
            risk_score=score,
            risk_class=RiskClass(risk_class) if isinstance(risk_class, str) else risk_class,
            confidence=confidence,
            method=self.name(),
            timestamp=0.0,
            features=to_jsonable(features),
        )


def _classify(score: float) -> RiskClass:
    if score < 0.34:
        return RiskClass.LOW
    if score < 0.67:
        return RiskClass.MEDIUM
    return RiskClass.HIGH


def create_predictor(cfg: Any, event_bus=None) -> tuple[RiskPredictor, bool]:
    """Factory: returns (predictor, is_mock). Falls back to deterministic.

    *cfg* is a Settings object.  When the configured ML backend is
    unavailable, publishes MODEL_FAILURE and falls back to the
    deterministic predictor with ``method`` clearly reported.
    """
    from core.events import EventType, Severity

    choice = cfg.get("risk.predictor", "deterministic_ttc")
    safe_min = cfg.get("safety.zones.safe_min_m", 2.5)
    high_speed = cfg.get("risk.high_closing_speed_mps", 1.0)
    ttc_warning = cfg.get("risk.ttc_warning_s", 3.0)

    if choice == "ml":
        path = cfg.get("risk.model_path")
        if not path:
            if event_bus:
                event_bus.publish(EventType.MODEL_FAILURE, Severity.WARNING, "ml",
                                  {"reason": "risk.model_path not configured"})
            return DeterministicTTCPredictor(safe_min, high_speed, ttc_warning), True
        try:
            return MLRiskPredictor(str(path), safe_min), False
        except PredictorUnavailable as exc:
            if event_bus:
                event_bus.publish(EventType.MODEL_FAILURE, Severity.WARNING, "ml",
                                  {"reason": str(exc)})
            return DeterministicTTCPredictor(safe_min, high_speed, ttc_warning), True

    if choice == "mock":
        return MockRiskPredictor(), True

    return DeterministicTTCPredictor(safe_min, high_speed, ttc_warning), False