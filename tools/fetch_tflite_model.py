#!/usr/bin/env python3
"""
tools/fetch_tflite_model.py — Download a TFLite object-detection model.

Ported from the v1 ``tinker-vision-alert`` download_model.py.  Fetches
EfficientDet-Lite0 or MobileNet-SSD v2 from the public TFLite model zoo
into ``models/detector/<name>/``.

Usage:
    python -m tools.fetch_tflite_model --model efficientdet_lite0
"""

from __future__ import annotations

import argparse
import os
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from core.config import PROJECT_ROOT

MODEL_SOURCES: dict[str, dict] = {
    "efficientdet_lite0": {
        "url": "https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_efficientdet_lite0_v1_1.0_quant_2019_08_26.zip",
        "model_filename": "efficientdet_lite0.tflite",
    },
    "efficientdet_lite1": {
        "url": "https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_efficientdet_lite1_v1_1.0_quant_2019_08_26.zip",
        "model_filename": "efficientdet_lite1.tflite",
    },
    "efficientdet_lite2": {
        "url": "https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_efficientdet_lite2_v1_1.0_quant_2019_08_26.zip",
        "model_filename": "efficientdet_lite2.tflite",
    },
    "ssd_mobilenet_v2": {
        "url": "https://storage.googleapis.com/download.tensorflow.org/models/tflite/ssd_mobilenet_v2_coco_2018_03_29.zip",
        "model_filename": "ssd_mobilenet_v2.tflite",
    },
}

LABELMAP_URL = "https://dl.google.com/coral/public/samples/coco_labels.txt"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a TFLite model.")
    parser.add_argument("--model", choices=list(MODEL_SOURCES),
                        default="efficientdet_lite0")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    src = MODEL_SOURCES[args.model]
    dest_dir = PROJECT_ROOT / "models" / "detector" / args.model
    dest_dir.mkdir(parents=True, exist_ok=True)
    model_path = dest_dir / src["model_filename"]

    if model_path.is_file() and not args.force:
        print(f"✓ Model already present: {model_path}")
    else:
        zip_path = dest_dir / "_download.zip"
        print(f"  Downloading {args.model} …")
        urllib.request.urlretrieve(src["url"], zip_path)
        if zipfile.is_zipfile(zip_path):
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(dest_dir)
        elif tarfile.is_tarfile(zip_path):
            with tarfile.open(zip_path, "r:*") as tf:
                tf.extractall(dest_dir)
        else:
            print("✗ Unknown archive format.")
            return 1
        found = False
        for f in dest_dir.rglob("*.tflite"):
            if f != model_path:
                f.replace(model_path)
            found = True
            break
        zip_path.unlink(missing_ok=True)
        if not found:
            print("✗ No .tflite inside the archive.")
            return 1
        print(f"✓ Model saved to {model_path}")

    label_path = dest_dir / "coco_labels.txt"
    if not label_path.is_file() or args.force:
        try:
            print("  Downloading COCO label map …")
            urllib.request.urlretrieve(LABELMAP_URL, label_path)
        except Exception as exc:
            print(f"  ⚠ Label map download failed ({exc}); the backend has "
                  "a built-in COCO fallback.")
    print("\n✓ Ready.  Set config.yaml → vision.backend: tflite to use it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())