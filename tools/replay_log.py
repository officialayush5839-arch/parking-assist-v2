#!/usr/bin/env python3
"""
tools/replay_log.py — Replay a recorded session without hardware.

Reads a JSONL session (from tools/collect_dataset.py or the runtime's
sensor/vision logs), feeds the records through the deterministic safety
engine, and prints the reproduced states + events.

Usage:
    python -m tools.replay_log data/raw/session_20260101_120000.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.config import load_config
from core.models import DistanceEstimate, SensorReading, Zone
from distance.monocular import MonocularDistanceEstimator
from fusion.confidence_fusion import ConfidenceFusion
from fusion.fusion_policy import FusionPolicy
from ml.risk_prediction import RiskFeatures, create_predictor
from ml.ttc import compute_ttc, ttc_display
from zone.safety_engine import DeterministicSafetyEngine
from zone.thresholds import ZoneThresholds


def load_records(path: str) -> list[dict]:
    records: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a recorded session.")
    parser.add_argument("path", help="JSONL session file.")
    parser.add_argument("--limit", type=int, default=0, help="Replay N cycles (0 = all).")
    args = parser.parse_args()

    if not Path(args.path).is_file():
        print(f"✗ File not found: {args.path}")
        return 1

    cfg = load_config()
    thresholds = ZoneThresholds.from_cfg(cfg)
    predictor, _ = create_predictor(cfg)
    fusion = ConfidenceFusion(FusionPolicy.from_cfg(cfg))
    monocular = MonocularDistanceEstimator(
        focal_length_px=float(cfg.get("distance.monocular.focal_length_px", 600.0)),
        known_widths_m=cfg.get("distance.monocular.known_widths_m", {}),
    )
    safety = DeterministicSafetyEngine(thresholds, cfg)

    records = load_records(args.path)
    cycles = [r for r in records if r.get("type") == "cycle"]
    if args.limit > 0:
        cycles = cycles[: args.limit]

    print(f"Replaying {len(cycles)} cycles from {args.path}\n")
    last_state = None
    for record in cycles:
        now = float(record.get("timestamp", 0.0))
        sensor_data = record.get("sensor") or {}
        reading = SensorReading(
            source=sensor_data.get("source", "replayed"),
            distance_m=sensor_data.get("distance_m"),
            valid=bool(sensor_data.get("valid", False)),
            timestamp=float(sensor_data.get("timestamp", now)),
            sequence=int(sensor_data.get("sequence", 0)),
            reason=sensor_data.get("reason"),
        )

        # Rebuild the best vision estimate from logged monocular/fused data.
        vision_est = None
        vision_est = DistanceEstimate(
            distance_m=record.get("telemetry", {}).get("distance_m"),
            confidence=float(record.get("telemetry", {}).get("confidence", 0.0)),
            method="replayed",
            valid=True,
            timestamp=now,
        )

        fusion_result = fusion.fuse(reading, vision_est, now)
        closing_speed = None
        decision = safety.evaluate(fusion_result, reading, vision_est,
                                   risk=None, closing_speed_mps=closing_speed, now=now)

        if decision.state != last_state:
            print(f"[t={now - (cycles[0].get('timestamp') or now):7.2f}s] "
                  f"STATE → {decision.state.value}  "
                  f"reasons={decision.reason_codes}")
            last_state = decision.state

    print(f"\nFinal state: {safety.state.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())