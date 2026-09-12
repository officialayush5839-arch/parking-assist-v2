#!/usr/bin/env python3
"""
tools/camera_test.py — Camera detection and testing tool.

Tests camera hardware and reports detection status.

Usage:
    python -m tools.camera_test
    python -m tools.camera_test --backend usb
    python -m tools.camera_test --backend mipi
    python -m tools.camera_test --backend video --video-file sample.mp4
"""

from __future__ import annotations

import argparse
import sys
import time

from app.config import load_config


def test_camera(backend: str, source, width: int, height: int, video_file: str | None) -> dict:
    """Test a camera backend and return results."""
    results = {
        "backend": backend,
        "detected": False,
        "resolution": None,
        "fps": None,
        "frames_captured": 0,
        "error": None,
    }

    try:
        if backend == "video":
            from camera.video_camera import VideoFileCamera
            cam = VideoFileCamera(video_file or "data/recordings/sample.mp4")
        elif backend == "mipi":
            from camera.mipi_camera import MIPICamera
            cam = MIPICamera(
                source=source,
                width=width,
                height=height,
                target_fps=15,
            )
        elif backend == "mock":
            from camera.mock_camera import MockCamera
            cam = MockCamera(width=width, height=height)
        else:  # usb
            from camera.usb_camera import USBCamera
            cam = USBCamera(
                source=source,
                width=width,
                height=height,
                target_fps=15,
            )

        cam.start()
        results["detected"] = True

        # Get resolution
        frame = cam.read()
        if frame is not None:
            h, w = frame.shape[:2]
            results["resolution"] = f"{w}x{h}"
            results["frames_captured"] = 1

            # Try to measure FPS
            start = time.time()
            for _ in range(30):
                frame = cam.read()
                if frame is not None:
                    results["frames_captured"] += 1
            elapsed = time.time() - start
            if elapsed > 0:
                results["fps"] = results["frames_captured"] / elapsed

        cam.stop()

    except Exception as e:
        results["error"] = str(e)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Camera detection and testing tool")
    parser.add_argument(
        "--backend",
        choices=["auto", "usb", "mipi", "video", "mock"],
        default="auto",
        help="Camera backend to test (default: auto)",
    )
    parser.add_argument("--source", type=int, default=0, help="Camera source index or path")
    parser.add_argument("--width", type=int, default=640, help="Frame width")
    parser.add_argument("--height", type=int, default=480, help="Frame height")
    parser.add_argument("--video-file", type=str, default=None, help="Video file path")
    args = parser.parse_args()

    print("=" * 50)
    print("CAMERA TEST")
    print("=" * 50)
    print()

    cfg = load_config()
    backend = args.backend if args.backend != "auto" else cfg.get("camera.backend", "auto")

    results = test_camera(
        backend=backend,
        source=args.source,
        width=args.width,
        height=args.height,
        video_file=args.video_file,
    )

    print(f"Camera detected: {'YES' if results['detected'] else 'NO'}")
    if results["resolution"]:
        print(f"Resolution: {results['resolution']}")
    if results["fps"]:
        print(f"FPS: {results['fps']:.1f}")
    print(f"Frames captured: {results['frames_captured']}")

    if results["error"]:
        print(f"Error: {results['error']}")

    print()
    print("=" * 50)

    if results["detected"]:
        print("RESULT: CAMERA OK")
        return 0
    else:
        print("RESULT: CAMERA FAILED")
        if backend != "mock" and backend != "video":
            print("Note: Falling back to mock camera may be possible")
        return 1


if __name__ == "__main__":
    sys.exit(main())
