#!/usr/bin/env python3
"""
tools/benchmark.py — Performance benchmark (real measurements only).

Measures pipeline FPS, per-stage latency, P95, CPU and RAM over
``--frames`` cycles using the configured (or mock) backends.  No values
are claimed unless actually measured here.

Usage:
    python -m tools.benchmark --frames 500
    python -m tools.benchmark --mode camera --frames 300
"""

from __future__ import annotations

import argparse
import sys
import time

from app.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark the pipeline.")
    parser.add_argument("--frames", type=int, default=500)
    parser.add_argument("--mode", default="simulation",
                        choices=["simulation", "camera", "hardware"])
    parser.add_argument("--scenario", default="vehicle_approaching_fast")
    args = parser.parse_args()

    cfg = load_config(overrides={
        "system": {"mode": args.mode, "scenario": args.scenario,
                   "verbose": False},
    })

    from app.runtime import Runtime
    from diagnostics.system_monitor import SystemMonitor

    print(f"Benchmark: mode={args.mode} frames={args.frames} "
          f"loop_hz={cfg.get('system.loop_hz')}")
    runtime = Runtime(cfg=cfg, mode=args.mode, scenario_name=args.scenario)
    monitor = SystemMonitor()

    start = time.monotonic()
    for _ in range(args.frames):
        now = time.time()
        frame, frame_id, frame_ts = runtime.frame_reader.read()
        reading = runtime.sensor_reader.read()
        runtime.pipeline.step(frame=frame, frame_id=frame_id, frame_ts=frame_ts,
                              sensor_reading=reading,
                              camera_healthy=runtime.camera.healthy,
                              predictor_note=runtime.predictor.name())
    elapsed = time.monotonic() - start
    runtime.shutdown()

    m = runtime.metrics.snapshot()
    measured_fps = args.frames / elapsed if elapsed > 0 else 0.0

    print(f"\nFrames      : {args.frames}")
    print(f"Average FPS : {measured_fps:.2f}  (measured over {elapsed:.2f}s)")
    print(f"Avg latency : {m['avg_cycle_ms']:.2f} ms")
    print(f"P95 latency : {m['p95_cycle_ms']:.2f} ms")
    print(f"CPU         : {monitor.cpu_percent()} %")
    print(f"RAM         : {monitor.ram_mb()} MB")
    if m["stage_avg_ms"]:
        print("Stages (avg ms): " + ", ".join(
            f"{k}={v:.2f}" for k, v in m["stage_avg_ms"].items()))
    print("\nNOTE: measurements are for this host with the backends actually "
          "used (mock backends measure the pipeline, not real hardware).")
    return 0


if __name__ == "__main__":
    sys.exit(main())