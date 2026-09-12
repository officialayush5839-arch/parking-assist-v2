"""
ml/evaluation/evaluate_detector.py — Object detector evaluation scaffold.

Evaluates detection accuracy, precision, recall, and latency.
Requires a real evaluation dataset with ground-truth annotations.

Usage:
    python -m ml.evaluation.evaluate_detector --data data/processed/detections/
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
        description="Evaluate object detector (prototype)")
    parser.add_argument("--data", type=str, default=None,
                        help="Path to evaluation dataset")
    parser.add_argument("--model", type=str, default=None,
                        help="Path to model weights")
    args = parser.parse_args()

    print("=" * 60)
    print("  Detector Evaluation (prototype)")
    print("=" * 60)

    if args.data and Path(args.data).exists():
        print(f"Evaluating on {args.data}")
        # TODO: implement real evaluation
        print("WARNING: Full evaluation requires real annotated data.")
    else:
        print("No evaluation data provided. Use --data <path> to specify.")
        print("Expected format: images/ with annotations.json (COCO-style)")

    print("\nPlaceholder results (SYNTHETIC):")
    print("  mAP@0.5:    N/A (requires real data)")
    print("  Precision:  N/A")
    print("  Recall:     N/A")
    print("  FPS:        N/A (measure on target hardware)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
