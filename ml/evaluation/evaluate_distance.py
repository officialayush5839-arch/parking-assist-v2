"""
ml/evaluation/evaluate_distance.py — Distance estimation evaluation.

Compares monocular and ultrasonic distance estimates against ground truth.

Usage:
    python -m ml.evaluation.evaluate_distance --data data/processed/distance_log.jsonl
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
        description="Evaluate distance estimation (prototype)")
    parser.add_argument("--data", type=str, default=None)
    args = parser.parse_args()

    print("=" * 60)
    print("  Distance Estimation Evaluation (prototype)")
    print("=" * 60)

    if args.data and Path(args.data).exists():
        print(f"Evaluating on {args.data}")
        print("WARNING: Full evaluation requires ground-truth distances.")
    else:
        print("No evaluation data provided.")

    print("\nPlaceholder results (SYNTHETIC):")
    print("  Monocular MAE:  N/A")
    print("  Ultrasonic MAE: N/A")
    print("  Fusion MAE:     N/A")

    return 0


if __name__ == "__main__":
    sys.exit(main())
