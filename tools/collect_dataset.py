#!/usr/bin/env python3
"""
tools/collect_dataset.py — Record sensor/vision data for ML datasets.

Runs a short recording session (camera or simulation) and writes:
  * data/raw/session_<ts>.jsonl  — sensor readings, detections, safety state
  * data/raw/frames_<ts>/        — sampled JPEG frames

Recordings are tagged with the source mode so synthetic data is never
mistaken for real data (see docs/ml.md).

Usage:
    python -m tools.collect_dataset --mode simulation --scenario vehicle_approaching_fast --seconds 20
    python -m tools.collect_dataset --mode camera --seconds 30 --save-frames
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from app.config import load_config
from core.models import to_jsonable

DATA_ROOT = Path(__file__).resolve().parent.parent / "data" / "raw"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect dataset recordings.")
    parser.add_argument("--mode", default="simulation",
                        choices=["simulation", "camera", "hardware"])
    parser.add_argument("--scenario", default="vehicle_approaching_fast")
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--save-frames", action="store_true",
                        help="Save sampled frames as JPEGs.")
    args = parser.parse_args()

    cfg = load_config()
    overrides = {"system": {"mode": args.mode, "scenario": args.scenario,
                            "duration_s": args.seconds}}
    cfg = load_config(overrides=overrides)

    from app.runtime import Runtime

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_path = DATA_ROOT / f"session_{stamp}.jsonl"
    frame_dir = DATA_ROOT / f"frames_{stamp}"
    frame_dir.mkdir(parents=True, exist_ok=True)
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    runtime = Runtime(cfg=cfg, mode=args.mode, scenario_name=args.scenario,
                      duration_s=args.seconds)
    fh = open(session_path, "w", encoding="utf-8")

    print(f"Collecting {args.seconds}s of {args.mode} data → {session_path}")
    start = time.time()
    last_frame_save = 0.0
    try:
        while time.time() - start < args.seconds:
            now = time.time()
            frame, frame_id, frame_ts = runtime.frame_reader.read()
            reading = runtime.sensor_reader.read()
            telemetry = runtime.pipeline.step(
                frame=frame, frame_id=frame_id, frame_ts=frame_ts,
                sensor_reading=reading,
                camera_healthy=runtime.camera.healthy,
                predictor_note=runtime.predictor.name())

            record = {
                "type": "cycle",
                "source": args.mode,
                "timestamp": now,
                "sensor": to_jsonable(reading),
                "telemetry": to_jsonable(telemetry),
                "detections": [to_jsonable(d) for d in runtime.pipeline._last_detections],
                "tracks": [to_jsonable(t) for t in runtime.pipeline._last_tracks],
            }
            fh.write(json.dumps(record, default=str) + "\n")
            fh.flush()

            if args.save_frames and frame is not None and now - last_frame_save >= 0.5:
                last_frame_save = now
                import cv2  # type: ignore  # noqa: PLC0415

                cv2.imwrite(str(frame_dir / f"frame_{frame_id:06d}.jpg"), frame)

            import time as _t
            _t.sleep(1.0 / max(1, int(cfg.get("system.loop_hz", 15))))
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        fh.close()
        runtime.shutdown()

    print(f"✓ Session saved: {session_path}")
    if args.save_frames:
        print(f"✓ Frames saved: {frame_dir}")
    print("  Replay with: python -m tools.replay_log <session file>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())