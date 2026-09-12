"""
ml/training/train_anomaly_model.py — Anomaly detection model training.

Trains an Isolation Forest for system health monitoring (diagnostics).
This is an OPTIONAL component that supports diagnostics, not safety.

Usage:
    python -m ml.training.train_anomaly_model --synthetic-samples 500
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def generate_synthetic_features(n: int = 500) -> list[list[float]]:
    """Generate synthetic sensor/health features for anomaly detection."""
    import random
    random.seed(42)
    features = []
    for _ in range(n):
        features.append([
            random.uniform(0.2, 5.0),    # distance_m
            random.uniform(0, 3.0),       # closing_speed_mps
            random.uniform(10, 20),       # fps
            random.uniform(20, 100),      # inference_latency_ms
            random.uniform(0.3, 0.95),    # detector_confidence
            random.uniform(0, 0.5),       # sensor_disagreement_m
            random.uniform(30, 80),       # cpu_percent
            random.uniform(200, 600),     # memory_mb
        ])
    return features


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train anomaly detection model (diagnostics, optional)")
    parser.add_argument("--synthetic-samples", type=int, default=500)
    args = parser.parse_args()

    print("=" * 60)
    print("  Anomaly Detection Model Training (prototype)")
    print("=" * 60)

    try:
        from sklearn.ensemble import IsolationForest
        import numpy as np

        data = np.array(generate_synthetic_features(args.synthetic_samples))
        print(f"Training Isolation Forest on {len(data)} samples...")

        start = time.time()
        model = IsolationForest(
            n_estimators=100, contamination=0.05, random_state=42)
        model.fit(data)
        elapsed = time.time() - start

        print(f"Training completed in {elapsed:.2f}s")
        print(f"Score range: {model.score_samples(data).min():.4f} to "
              f"{model.score_samples(data).max():.4f}")
        print("\nNOTE: SYNTHETIC data only. Real anomaly detection requires")
        print("      real system health data.")
    except ImportError:
        print("scikit-learn not available. Skipping anomaly model training.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
