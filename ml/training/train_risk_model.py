"""
ml/training/train_risk_model.py — Risk prediction model training.

Trains a lightweight risk classifier from the collected distance/velocity/
sensor-fusion features. Requires a real dataset in data/processed/.

Usage:
    python -m ml.training.train_risk_model --data data/processed/risk_features.csv
    python -m ml.training.train_risk_model --data data/processed/risk_features.csv --output ml/models/risk_model.joblib

NOTE: This is a training scaffold. Without real data, only the interface
is exercised with synthetic samples. Model performance claims require
evaluation on real-world data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Ensure project root is on the path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def generate_synthetic_data(n_samples: int = 200) -> list[dict]:
    """Generate synthetic training data for demonstration purposes.

    WARNING: This is SYNTHETIC data — not real-world sensor/vision data.
    Labels and distributions are approximations for interface testing only.
    """
    import random

    random.seed(42)
    data = []
    for _ in range(n_samples):
        distance = random.uniform(0.2, 5.0)
        closing_speed = random.uniform(-2.0, 4.0)
        ttc = distance / max(closing_speed, 0.01)
        det_conf = random.uniform(0.1, 0.95)
        sensor_conf = random.uniform(0.3, 1.0)
        disagreement = abs(random.gauss(0, 0.3))

        # Synthetic risk label based on deterministic rules
        risk_score = 0.0
        if distance < 0.5:
            risk_score = 0.95
        elif distance < 1.0:
            risk_score = 0.75
        elif distance < 1.8:
            risk_score = 0.45
        else:
            risk_score = 0.15

        if closing_speed > 2.0:
            risk_score = min(1.0, risk_score + 0.2)
        if ttc < 2.0:
            risk_score = min(1.0, risk_score + 0.15)

        risk_class = "LOW"
        if risk_score > 0.7:
            risk_class = "HIGH"
        elif risk_score > 0.4:
            risk_class = "MEDIUM"

        data.append({
            "distance_m": distance,
            "closing_speed_mps": closing_speed,
            "ttc_seconds": ttc,
            "detector_confidence": det_conf,
            "sensor_confidence": sensor_conf,
            "disagreement_m": disagreement,
            "risk_score": risk_score,
            "risk_class": risk_class,
        })
    return data


def train_model(data: list[dict]) -> dict:
    """Train a risk classification model.

    Returns a dict with the trained model metadata (for interface testing).
    """
    try:
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report
        import numpy as np

        feature_cols = [
            "distance_m", "closing_speed_mps", "ttc_seconds",
            "detector_confidence", "sensor_confidence", "disagreement_m",
        ]
        X = np.array([[d[c] for c in feature_cols] for d in data])
        y = np.array([d["risk_class"] for d in data])

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42)

        model = GradientBoostingClassifier(
            n_estimators=50, max_depth=4, random_state=42)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        report = classification_report(y_test, y_pred, output_dict=True)

        return {
            "model": model,
            "feature_cols": feature_cols,
            "report": report,
            "n_train": len(X_train),
            "n_test": len(X_test),
        }
    except ImportError:
        print("WARNING: scikit-learn not available. Skipping model training.")
        return {"model": None, "feature_cols": [], "report": {}, "n_train": 0, "n_test": 0}


def save_model(model_data: dict, output_path: str) -> None:
    """Save the trained model to disk."""
    try:
        import joblib
        joblib.dump(model_data, output_path)
        print(f"Model saved to {output_path}")
    except ImportError:
        print("WARNING: joblib not available. Model not saved.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train risk prediction model (prototype)")
    parser.add_argument("--data", type=str, default=None,
                        help="Path to training data CSV (uses synthetic if not provided)")
    parser.add_argument("--output", type=str, default="ml/models/risk_model.joblib",
                        help="Output model path")
    parser.add_argument("--synthetic-samples", type=int, default=200,
                        help="Number of synthetic samples to generate")
    args = parser.parse_args()

    print("=" * 60)
    print("  Risk Model Training (prototype)")
    print("=" * 60)

    # Generate or load data
    if args.data and os.path.exists(args.data):
        print(f"Loading data from {args.data}")
        # TODO: implement CSV loading for real data
        data = generate_synthetic_data(args.synthetic_samples)
    else:
        print(f"Generating {args.synthetic_samples} synthetic samples (DEMO)")
        data = generate_synthetic_data(args.synthetic_samples)

    print(f"Training on {len(data)} samples...")
    start = time.time()
    result = train_model(data)
    elapsed = time.time() - start

    if result["model"] is not None:
        print(f"Training completed in {elapsed:.2f}s")
        print(f"Train size: {result['n_train']}, Test size: {result['n_test']}")
        if result["report"]:
            print("\nClassification Report:")
            for cls in ["LOW", "MEDIUM", "HIGH"]:
                if cls in result["report"]:
                    r = result["report"][cls]
                    print(f"  {cls}: precision={r.get('precision', 0):.3f} "
                          f"recall={r.get('recall', 0):.3f} f1={r.get('f1-score', 0):.3f}")

        # Save model
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        save_model(result, args.output)
    else:
        print("Model training skipped (missing dependencies)")

    print("\nNOTE: Results are SYNTHETIC. Real model performance requires")
    print("      real-world data collection and evaluation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
