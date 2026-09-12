# KPIT Parking Assist V2.0 — Architecture

## Overview

The system is an edge-based parking-assistance and obstacle-awareness system. AI/ML improves perception and prediction but NEVER overrides hard safety conditions.

## Pipeline Architecture

```
Camera (MIPI CSI / USB / Mock)
        ↓
  Image Preprocessing (resize, normalize, ROI, denoise)
        ↓
  Object Detection (YOLOv8n / TFLite / Mock)
        ↓
  Object Tracking (IOU / ByteTrack)
        ↓
  Monocular Distance Estimation (pinhole geometry)
        ↓
  ┌─────────────────────────────┐
  │    Sensor / Vision Fusion   │
  │  (weighted, validity-gated) │
  └──────────────┬──────────────┘
                 ↓
  Ultrasonic Distance (JSN-SR04T / Mock)
                 ↓
  Closing Speed Estimation (EMA-smoothed)
                 ↓
  Time-to-Collision (TTC)
                 ↓
  ML Risk Prediction (advisory only)
                 ↓
  ┌─────────────────────────────┐
  │   Deterministic Safety      │
  │       Engine                │
  │  (hard limits > ML)         │
  └──────────────┬──────────────┘
                 ↓
  ┌──────────┬──────────┬──────────┐
  ↓          ↓          ↓          ↓
 LED       Buzzer      LCD      Logging
```

## Module Responsibilities

### Camera (`camera/`)
- `interface.py` — Abstract `CameraInterface` (start/read/stop)
- `mock_camera.py` — Synthetic frame generation
- `usb_camera.py` — OpenCV VideoCapture backend
- `mipi_camera.py` — MIPI CSI backend (Tinker Board)
- `video_camera.py` — Video file playback
- `calibration.py` — Camera intrinsic calibration (OpenCV)
- `preprocessing.py` — Frame resize, normalize, denoise, ROI

### Vision (`vision/`)
- `detector.py` — `ObjectDetector` facade with backend switching
- `yolo_backend.py` — YOLOv8n via ultralytics
- `mock_detector.py` — Scripted/mock detections
- `preprocessing.py` — Vision-specific preprocessing

### Tracking (`tracking/`)
- `tracker.py` — `ObjectTracker` ABC
- `iou_tracker.py` — Lightweight IOU-based tracker
- `bytetrack_backend.py` — ByteTrack wrapper
- `velocity.py` — Closing-speed estimation per track

### Distance (`distance/`)
- `ultrasonic.py` — Ultrasonic sensor interface + mock
- `monocular.py` — Pinhole geometry distance estimation
- `distance_validator.py` — Range/timestamp validation

### Fusion (`fusion/`)
- `confidence_fusion.py` — Weighted fusion with validity gating
- `fusion_policy.py` — Configurable fusion policy

### Safety (`zone/`)
- `safety_engine.py` — Deterministic safety decision engine
- `state_machine.py` — Hysteresis state machine
- `thresholds.py` — Configurable zone thresholds

### Alerts (`alerts/`)
- `led_controller.py` — LED state mapping
- `buzzer_controller.py` — Buzzer pattern control
- `scheduler.py` — Non-blocking alert scheduling

### Display (`display/`)
- `lcd.py` — 20x4 I2C LCD interface
- `hmi.py` — HMI page scheduler
- `mock_display.py` — Console output display

### Diagnostics (`diagnostics/`)
- `health.py` — Component health tracking
- `metrics.py` — FPS, latency, per-stage timing
- `system_monitor.py` — CPU, RAM, temperature

## Data Flow

Every measurement includes:
- `timestamp` — When it was captured
- `source` — Origin module
- `sequence/frame_id` — Ordering
- `validity` — Whether the measurement is trustworthy

## Failure Management

| Fault | Detection | Response |
|---|---|---|
| Camera failure | No frames / timeout | Use ultrasonic only |
| Sensor timeout | Read timeout | Use vision only |
| Detector failure | Exception / no output | Log, use last known |
| Tracker failure | Exception | Reset, re-detect |
| Calibration missing | Config check | Approximate distance |
| Sensor disagreement | Large distance delta | Conservative policy |
| Both invalid | No valid distance | FAULT state |

## Safety Guarantee

The fundamental safety guarantee is:

```
IF ultrasonic_valid AND ultrasonic_distance <= critical_threshold:
    state = CRITICAL
    ALWAYS, regardless of:
      - vision_confidence = 0
      - detector failed
      - tracker lost
      - ML risk = LOW
      - vision says 100m away
```

This rule is tested by `test_hard_safety_override` and `test_ai_cannot_veto_hard_safety`.
