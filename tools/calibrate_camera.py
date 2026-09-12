#!/usr/bin/env python3
"""
tools/calibrate_camera.py — OpenCV chessboard calibration.

Captures N frames of a chessboard from the camera and writes
``config/camera_calibration.yaml`` (intrinsics, distortion, size,
version).  Run ``--mode camera`` afterwards to use calibrated monocular
distance.

Usage:
    python -m tools.calibrate_camera --camera 0 --rows 9 --cols 6 --frames 20
"""

from __future__ import annotations

import argparse
import time

import cv2  # type: ignore
import numpy as np  # type: ignore

from camera.calibration import CameraCalibration, CALIBRATION_VERSION
from core.config import PROJECT_ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="Chessboard camera calibration.")
    parser.add_argument("--camera", type=str, default="0")
    parser.add_argument("--rows", type=int, default=9, help="inner corners per row")
    parser.add_argument("--cols", type=int, default=6, help="inner corners per column")
    parser.add_argument("--frames", type=int, default=20)
    parser.add_argument("--square-size", type=float, default=0.025, help="square side (m)")
    parser.add_argument("--out", type=str, default=str(PROJECT_ROOT / "config" / "camera_calibration.yaml"))
    args = parser.parse_args()

    rows, cols = args.rows, args.cols
    pattern = (cols, rows)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    objp = np.zeros((rows * cols, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2) * args.square_size

    obj_points: list[np.ndarray] = []
    img_points: list[np.ndarray] = []
    captured = 0

    src = int(args.camera) if args.camera.isdigit() else args.camera
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        print(f"✗ Cannot open camera {src}")
        return 1

    print(f"Show the {cols}x{rows} chessboard to the camera. "
          f"Collecting {args.frames} frames — press SPACE to capture, ESC to quit.")

    while captured < args.frames:
        ok, frame = cap.read()
        if not ok:
            print("⚠ Frame read failed; retrying …")
            time.sleep(0.2)
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found, corners = cv2.findChessboardCorners(gray, pattern, None)
        display = frame.copy()
        if found:
            cv2.drawChessboardCorners(display, pattern, corners, found)
        cv2.imshow("Calibrate", display)
        key = cv2.waitKey(15) & 0xFF
        if key == 27:
            break
        if key == ord(" ") and found:
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            obj_points.append(objp)
            img_points.append(corners2)
            captured += 1
            print(f"  captured {captured}/{args.frames}")

    cap.release()
    cv2.destroyAllWindows()

    if len(obj_points) < 5:
        print("✗ Not enough frames captured (need ≥ 5).")
        return 1

    h, w = gray.shape[:2]
    ret, mtx, dist, _rvecs, _tvecs = cv2.calibrateCamera(
        obj_points, img_points, (w, h), None, None)
    if not ret:
        print("✗ Calibration failed.")
        return 1

    calibration = CameraCalibration(
        camera_matrix=mtx.tolist(),
        dist_coeffs=dist.flatten().tolist(),
        image_width=w,
        image_height=h,
        version=CALIBRATION_VERSION,
    )
    calibration.save(args.out)
    print(f"\n✓ Calibration written to {args.out}")
    print(f"  fx={mtx[0, 0]:.2f}  fy={mtx[1, 1]:.2f}  "
          f"cx={mtx[0, 2]:.2f}  cy={mtx[1, 2]:.2f}")
    print("  Monocular distance estimation will use fx automatically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())