"""
ml/anomaly.py — Optional anomaly detection (Isolation Forest).

Anomaly detection supports **diagnostics only** — it never changes the
safety state and is not required for basic operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from core.errors import ComponentUnavailable


@dataclass
class AnomalyResult:
    score: float          # 0..1, higher = more anomalous
    is_anomaly: bool
    method: str


class AnomalyDetector:
    """Isolation-Forest-based anomaly scorer (lazy sklearn import)."""

    FEATURE_NAMES = [
        "sensor_distance_m", "fps", "inference_latency_ms",
        "detector_confidence", "tracking_stability", "disagreement",
        "cpu_percent", "ram_mb",
    ]

    def __init__(self, enabled: bool = False, contamination: float = 0.05) -> None:
        self._enabled = bool(enabled)
        self._contamination = float(contamination)
        self._model: Any = None
        self._fitted = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from sklearn.ensemble import IsolationForest  # type: ignore
        except ImportError as exc:
            raise ComponentUnavailable("scikit-learn required for anomaly detection") from exc
        self._model = IsolationForest(
            contamination=self._contamination, random_state=42, n_jobs=1,
        )

    def fit(self, rows: list[list[float]]) -> None:
        """Fit on historical feature rows (e.g. from experiment logs)."""
        if not self._enabled or not rows:
            return
        self._ensure_model()
        import numpy as np  # type: ignore

        self._model.fit(np.asarray(rows, dtype=float))
        self._fitted = True

    def predict(self, features: dict[str, Optional[float]]) -> AnomalyResult:
        """Score one observation. Returns non-anomalous when disabled/not fitted."""
        if not self._enabled or not self._fitted:
            return AnomalyResult(score=0.0, is_anomaly=False, method="disabled")

        row = [features.get(name, -1.0) for name in self.FEATURE_NAMES]
        try:
            import numpy as np  # type: ignore

            score = float(self._model.score_samples(np.asarray([row], dtype=float))[0])
            label = int(self._model.predict(np.asarray([row], dtype=float))[0])
            # IsolationForest scores: higher = normal.  Normalise to 0..1.
            anomaly_score = _clamp01(0.5 - score / 2.0)
            return AnomalyResult(
                score=anomaly_score,
                is_anomaly=bool(label == -1),
                method="isolation_forest",
            )
        except Exception:
            return AnomalyResult(score=0.0, is_anomaly=False, method="error")


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))