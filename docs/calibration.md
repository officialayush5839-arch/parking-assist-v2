# Camera Calibration Guide

## Why Calibrate?

Monocular distance estimation depends on accurate camera intrinsic parameters (focal length, distortion coefficients). An uncalibrated camera produces approximate distances only.

## Calibration Procedure

1. Print a checkerboard pattern (e.g., 9x6, 25mm squares)
2. Capture 20-30 images of the checkerboard at various angles
3. Run the calibration tool:

```bash
python -m tools.calibrate_camera --images data/calibration/ --output config/camera_calibration.yaml
```

4. Verify the output contains:
   - Intrinsic matrix (3x3)
   - Distortion coefficients
   - Image dimensions
   - Reprojection error (< 1.0 pixel is good)

## Calibration Output

```yaml
camera:
  calibration:
    version: 1.0
    image_width: 640
    image_height: 480
    intrinsic_matrix:
      - [612.3, 0.0, 319.5]
      - [0.0, 612.1, 239.8]
      - [0.0, 0.0, 1.0]
    distortion_coefficients: [0.01, -0.02, 0.0, 0.0, 0.0]
    reprojection_error: 0.45
```

## Without Calibration

The system works but:
- Reports `CALIBRATION_MISSING`
- Uses a default focal length (600px)
- Monocular distance estimates are approximate
- Confidence is reduced by 50%

## Recalibration

Recalibrate when:
- Camera or lens is replaced
- Mounting position changes
- Distance estimates become inconsistent
