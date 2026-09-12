#!/usr/bin/env python3
"""
tools/fetch_yolo_weights.py — Download YOLO weights into models/detector/.

The pipeline NEVER downloads weights automatically; run this explicitly
when you want the real YOLO backend.

Usage:
    python -m tools.fetch_yolo_weights            # yolov8n.pt
    python -m tools.fetch_yolo_weights --model yolov8s
"""

from __future__ import annotations

import argparse
from pathlib import Path

from core.config import PROJECT_ROOT

WEIGHTS_DIR = PROJECT_ROOT / "models" / "detector"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch YOLO weights.")
    parser.add_argument("--model", default="yolov8n",
                        help="ultralytics model name (yolov8n/s/m/l/x).")
    args = parser.parse_args()

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    target = WEIGHTS_DIR / f"{args.model}.pt"
    if target.is_file():
        print(f"✓ Weights already present: {target}")
        return 0

    print(f"Downloading {args.model} weights via ultralytics …")
    try:
        from ultralytics import YOLO  # type: ignore

        model = YOLO(args.model)  # downloads to the ultralytics cache
        source = Path(model.ckpt_path) if getattr(model, "ckpt_path", None) else None
    except Exception as exc:
        print(f"✗ Failed to fetch weights: {exc}")
        return 1

    if source and source.is_file():
        source.rename(target)
    print(f"✓ Weights saved to {target}")
    print("  Enable the YOLO backend: config.yaml → vision.backend: yolo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())