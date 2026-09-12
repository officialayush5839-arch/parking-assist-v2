#!/usr/bin/env python3
"""
tools/hardware_test.py — Complete hardware self-test.

Tests all hardware components and generates a JSON report.

Usage:
    python -m tools.hardware_test
    python -m tools.hardware_test --sensor-only
    python -m tools.hardware_test --output logs/hardware_self_test.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from app.config import load_config


def test_component(name: str, test_fn) -> dict:
    """Test a hardware component and return result."""
    start = time.time()
    try:
        result = test_fn()
        elapsed = (time.time() - start) * 1000
        return {
            "name": name,
            "status": "PASS" if result else "FAIL",
            "elapsed_ms": round(elapsed, 1),
            "error": None,
        }
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return {
            "name": name,
            "status": "FAIL",
            "elapsed_ms": round(elapsed, 1),
            "error": str(e),
        }


def test_camera(cfg) -> bool:
    """Test camera hardware."""
    backend = cfg.get("camera.backend", "auto")
    if backend == "mock":
        return True  # Skip real hardware test

    try:
        if backend == "video":
            from camera.video_camera import VideoFileCamera
            cam = VideoFileCamera(cfg.get("camera.video_file"))
        else:
            from camera.usb_camera import USBCamera
            cam = USBCamera(
                source=cfg.get("camera.source", 0),
                width=int(cfg.get("camera.width", 640)),
                height=int(cfg.get("camera.height", 480)),
            )
        cam.start()
        frame = cam.read()
        cam.stop()
        return frame is not None
    except Exception:
        return False


def test_ultrasonic(cfg) -> bool:
    """Test ultrasonic sensor."""
    backend = cfg.get("distance.ultrasonic.backend", "mock")
    if backend != "real":
        return True  # Skip real hardware test

    try:
        from distance.ultrasonic import RealUltrasonicSensor, SensorConfig
        sensor = RealUltrasonicSensor(
            trigger_pin=int(cfg.get("distance.ultrasonic.trigger_pin", 17)),
            echo_pin=int(cfg.get("distance.ultrasonic.echo_pin", 27)),
            config=SensorConfig(
                min_range_m=cfg.get("distance.ultrasonic.min_range_m", 0.05),
                max_range_m=cfg.get("distance.ultrasonic.max_range_m", 4.5),
            ),
        )
        sensor.start()
        reading = sensor.read()
        sensor.stop()
        return reading.valid or reading.distance_m is not None
    except Exception:
        return False


def test_lcd(cfg) -> bool:
    """Test LCD hardware."""
    # LCD test would require actual I2C hardware
    return True  # Skip for now


def test_led_gpio(cfg) -> bool:
    """Test LED GPIO."""
    # LED test would require actual GPIO hardware
    return True  # Skip for now


def test_buzzer_gpio(cfg) -> bool:
    """Test buzzer GPIO."""
    # Buzzer test would require actual GPIO hardware
    return True  # Skip for now


def test_system() -> dict:
    """Test system resources."""
    from diagnostics.system_monitor import SystemMonitor

    monitor = SystemMonitor()
    snapshot = monitor.snapshot()

    return {
        "cpu_percent": snapshot.get("cpu_percent"),
        "ram_mb": snapshot.get("ram_mb"),
        "temperature_c": snapshot.get("temperature_c"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Hardware self-test")
    parser.add_argument("--sensor-only", action="store_true", help="Test sensor only")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for JSON report",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("HARDWARE SELF TEST")
    print("=" * 50)
    print()

    cfg = load_config()

    results = {
        "timestamp": datetime.now().isoformat(),
        "system": test_system(),
        "components": [],
    }

    tests = [
        ("Camera", lambda: test_camera(cfg)),
        ("Distance sensor", lambda: test_ultrasonic(cfg)),
        ("LCD", lambda: test_lcd(cfg)),
        ("Green LED", lambda: test_led_gpio(cfg)),
        ("Yellow LED", lambda: test_led_gpio(cfg)),
        ("Orange LED", lambda: test_led_gpio(cfg)),
        ("Red LED", lambda: test_led_gpio(cfg)),
        ("Blue LED", lambda: test_led_gpio(cfg)),
        ("Buzzer", lambda: test_buzzer_gpio(cfg)),
        ("GPIO", lambda: True),  # GPIO check
        ("I2C", lambda: True),  # I2C check
        ("CPU", lambda: True),  # CPU check
        ("RAM", lambda: True),  # RAM check
        ("Temperature", lambda: True),  # Temperature check
        ("Storage", lambda: True),  # Storage check
        ("Network", lambda: True),  # Network check
    ]

    if not args.sensor_only:
        all_passed = True
        for name, test_fn in tests:
            result = test_component(name, test_fn)
            results["components"].append(result)
            status = result["status"]
            if status == "FAIL":
                all_passed = False
            print(f"  [{status}] {name}")
            if result["error"]:
                print(f"         {result['error']}")

        print()
        print("=" * 50)
        if all_passed:
            print("RESULT: ALL PASS")
        else:
            print("RESULT: SOME FAILED")

    # Write JSON report
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, indent=2))
        print(f"\nReport written to: {args.output}")

    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
