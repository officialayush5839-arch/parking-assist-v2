#!/usr/bin/env python3
"""
app/main.py — KPIT Parking Assist V2.0 CLI entry point.

Modes
-----
    simulation   — run a scripted scenario (no hardware, no camera needed)
    demo         — scripted SAFE→CAUTION→WARNING→CRITICAL showcase
    camera       — live camera (USB/MIPI/video) with mock sensor/detector
                   when real ones are unavailable
    hardware     — attempt real hardware backends; falls back to mocks
    selftest     — run hardware-independent component checks, then exit
    diagnostics  — print a system-health snapshot, then exit

Examples
--------
    python -m app.main --mode simulation --scenario vehicle_approaching_fast
    python -m app.main --mode simulation --scenario critical_distance
    python -m app.main --mode demo --dashboard
    python -m app.main --mode camera
    python -m app.main --mode hardware
    python -m app.main --mode selftest
    python -m app.main --list-scenarios
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from app.config import load_config
from app.runtime import Runtime, run_self_test
from core.config import PROJECT_ROOT


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.main",
        description="KPIT Parking Assist V2 — edge parking-safety prototype.",
    )
    parser.add_argument("--mode", choices=["simulation", "camera", "hardware",
                                           "demo", "selftest", "diagnostics"],
                        default=None, help="Runtime mode (default from config).")
    parser.add_argument("--scenario", default=None,
                        help="Simulation scenario name (see --list-scenarios).")
    parser.add_argument("--duration", type=float, default=None,
                        help="Run for N seconds (0 = scenario/default).")
    parser.add_argument("--config", default=None,
                        help="Path to a directory containing config/*.yaml.")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose per-cycle telemetry.")
    parser.add_argument("--dashboard", action="store_true",
                        help="Start the local diagnostics dashboard.")
    parser.add_argument("--list-scenarios", action="store_true",
                        help="List available simulation scenarios and exit.")
    return parser.parse_args(argv)


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    cfg = load_config(config_dir=args.config)

    if args.list_scenarios:
        from simulation.scenarios import available

        print("Available scenarios:")
        for name in available():
            print(f"  {name}")
        return 0

    mode = args.mode or cfg.get("system.mode", "simulation")

    overrides: dict = {}
    if args.verbose:
        overrides["system"] = {"verbose": True}
    if args.dashboard:
        overrides.setdefault("dashboard", {})["enabled"] = True
    if overrides:
        cfg = load_config(config_dir=args.config, overrides=overrides)

    _setup_logging(cfg.get("logging.level", "INFO"))

    print("=" * 64)
    print("  KPIT Parking Assist V2.0 - prototype (research/demo, not certified)")
    print("=" * 64)
    print(f"  Mode      : {mode}")
    if mode in ("simulation", "demo"):
        scenario_name = (args.scenario
                         or cfg.get("system.scenario")
                         or ("demo_sequence" if mode == "demo" else "vehicle_approaching_fast"))
        print(f"  Scenario  : {scenario_name}")
    print(f"  Loop      : {cfg.get('system.loop_hz')} Hz")
    print(f"  Dashboard : {'on' if cfg.get('dashboard.enabled') else 'off'}")
    print()

    if mode == "selftest":
        return run_self_test(cfg)

    if mode == "diagnostics":
        return _print_diagnostics(cfg)

    runtime = Runtime(cfg=cfg, mode=mode, scenario_name=args.scenario,
                      duration_s=args.duration,
                      dashboard_enabled=cfg.get("dashboard.enabled", False))
    return runtime.run()


def _print_diagnostics(cfg) -> int:
    from diagnostics.health import HealthMonitor
    from diagnostics.metrics import MetricsCollector
    from diagnostics.system_monitor import SystemMonitor

    monitor = SystemMonitor()
    print("System diagnostics")
    print(f"  CPU      : {monitor.cpu_percent()} %")
    print(f"  RAM      : {monitor.ram_mb()} MB")
    print(f"  Temp     : {monitor.temperature_c()} °C" if monitor.temperature_c() is not None
          else "  Temp     : n/a")
    print(f"  Config   : {PROJECT_ROOT / 'config'}")
    print("  (Run a mode with --dashboard for live monitoring.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())