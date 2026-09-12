"""
ml/evaluation/evaluate_risk.py — Risk prediction model evaluation.

Evaluates risk classification accuracy and calibration.

Usage:
    python -m ml.evaluation.evaluate_risk --data data/processed/risk_features.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate risk prediction model (prototype)")
    parser.add_argument("--data", type=str, default=None)
    parser.add_argument("--model", type=str, default="ml/models/risk_model.joblib")
    args = parser.parse_args()

    print("=" * 60)
    print("  Risk Model Evaluation (prototype)")
    print("=" * 60)

    if args.data and Path(args.data).exists():
        print(f"Evaluating on {args.data}")
        print("WARNING: Full evaluation requires real risk labels.")
    else:
        print("No evaluation data provided.")

    print("\nPlaceholder results (SYNTHETIC):")
    print("  Accuracy:     N/A")
    print("  F1 (macro):   N/A")
    print("  Brier score:  N/A")

    return 0


if __name__ == "__main__":
    sys.exit(main())
