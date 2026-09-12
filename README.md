# KPIT Parking Assist V2.0

**Edge parking-assist and obstacle-awareness system combining camera-based computer vision, ultrasonic sensing, sensor/vision fusion, and deterministic safety zones.**

> ⚠️ **PROTOTYPE** — This is a research/demo system. It is NOT certified for production automotive use. All thresholds are initial values requiring experimental validation.

---

## 1. Architecture

```
Camera + Ultrasonic Acquisition
        ↓
  Image Preprocessing
        ↓
  Object Detection (YOLO / Mock)
        ↓
  Object Tracking (IOU / ByteTrack)
        ↓
  Monocular Distance Estimation
        ↓
              ┌──────────────────┐
Ultrasonic ──→│  Sensor/Vision   │
              │     Fusion       │
              └────────┬─────────┘
                       ↓
               Risk / TTC Prediction
                       ↓
            Deterministic Safety Engine
                       ↓
              ┌────────┼────────┐
              ↓        ↓        ↓
             LCD      LED    Buzzer
```

### Core Engineering Principle

> **AI/ML is advisory. Deterministic safety logic is authoritative.**

A neural network alone NEVER decides whether the vehicle is safe. Hard safety rules always win. If the ultrasonic sensor reports an extremely short distance, the system enters CRITICAL even if vision confidence is 0 and ML risk is LOW.

### Decision Hierarchy (highest authority first)

1. Sensor health
2. Hard safety limits
3. Sensor + vision validation/fusion
4. ML confidence/risk score
5. Deterministic safety state machine
6. Alert scheduler
7. HMI/display/diagnostics

---

## 2. Installation

### Core (required for simulation/testing)

```bash
cd parking_assist_v2
pip install -r requirements.txt
```

Or minimal core only:

```bash
pip install numpy PyYAML psutil pytest
```

### Optional Groups

```bash
# Vision (OpenCV + YOLO)
pip install opencv-python ultralytics

# ML (risk/anomaly models)
pip install scikit-learn

# Dashboard
pip install fastapi uvicorn
```

---

## 3. Simulation Mode

Run without any hardware:

```bash
python -m app.main --mode simulation
python -m app.main --mode simulation --scenario critical_distance
python -m app.main --mode simulation --scenario vehicle_approaching_slow
python -m app.main --mode demo
```

### Available Scenarios

| Scenario | Description | Expected States |
|---|---|---|
| `safe_vehicle_stationary` | Vehicle at ~4m, stationary | SAFE |
| `vehicle_approaching_slow` | Slow approach (~0.2 m/s) | SAFE → CAUTION → WARNING |
| `vehicle_approaching_fast` | Fast approach (~0.35 m/s) | SAFE → CAUTION → WARNING → CRITICAL |
| `pedestrian_crossing` | Pedestrian crossing lateral | CAUTION / WARNING |
| `obstacle_near` | Static obstacle at 0.8m | WARNING |
| `ultrasonic_timeout` | US drops out at t=1s | Degraded from vision |
| `camera_failure` | Camera fails at t=3s | Continues on ultrasonic |
| `vision_low_confidence` | Low vision confidence | Sensor-driven |
| `sensor_disagreement` | US=0.9m vs Vision=4.0m | WARNING (conservative) |
| `critical_distance` | US=0.3m, no vision | CRITICAL (hard override) |

---

## 4. Camera Mode

Use a USB webcam or video file:

```bash
python -m app.main --mode camera
python -m app.main --mode camera --camera video --video-file recording.mp4
```

---

## 5. Hardware Mode

On the target board (e.g., ASUS Tinker Board R2.0):

```bash
python -m app.main --mode hardware
```

Requires: MIPI CSI camera, JSN-SR04T ultrasonic, I2C LCD, GPIO LEDs/buzzer.

---

## 6. Dashboard

Local diagnostics web UI:

```bash
python -m app.main --mode simulation --dashboard
# Open http://127.0.0.1:8765
```

---

## 7. Configuration

All settings in `config/`:

- `config.yaml` — main system config
- `safety.yaml` — safety zone thresholds
- `camera.yaml` — camera settings
- `logging.yaml` — logging config

### Example Safety Thresholds (DEMO values)

```yaml
safety:
  zones:
    safe_min_m: 2.5
    caution_min_m: 1.8
    warning_min_m: 1.0
    critical_min_m: 0.5
```

⚠️ These are initial values. They MUST be re-validated experimentally.

---

## 8. ML Models

### Detection

YOLOv8n (ultralytics) or mock detector. Model weights:

```bash
python -m tools.fetch_yolo_weights
```

If weights are unavailable, the system falls back to MOCK mode (clearly reported).

### Training

```bash
python -m ml.training.train_risk_model
python -m ml.training.train_anomaly_model
```

### Evaluation

```bash
python -m ml.evaluation.evaluate_detector --data data/processed/
python -m ml.evaluation.evaluate_distance --data data/processed/
python -m ml.evaluation.evaluate_risk --data data/processed/
```

⚠️ Training/evaluation scripts produce SYNTHETIC results without real data.

---

## 9. Calibration

```bash
python -m tools.calibrate_camera
```

Outputs `config/camera_calibration.yaml`. Without calibration, the system works but reports `CALIBRATION_MISSING` and monocular distance estimates are approximate.

---

## 10. Testing

```bash
# Run all tests
python -m pytest --import-mode=importlib -q

# Run specific test groups
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v
python -m pytest tests/simulation/ -v
```

### Key Safety Tests

- `test_hard_safety_override` — proves ML cannot veto critical ultrasonic
- `test_ai_cannot_veto_hard_safety` — ultrasonic 0.30m with LOW ML risk → CRITICAL
- `test_fault_when_both_sources_invalid` — both sensors invalid → FAULT

---

## 11. Hardware Deployment

See `docs/hardware.md` for target board wiring and GPIO configuration.

Target: ASUS Tinker Board R2.0 with:
- MIPI CSI camera
- JSN-SR04T ultrasonic sensor
- 20x4 I2C LCD
- 5 LEDs (green, yellow, orange, red, blue)
- 5V active buzzer
- Logic-level converter
- 5V regulated power supply

---

## 12. Project Structure

```
parking_assist_v2/
├── app/              # Main application, pipeline, runtime
├── camera/           # Camera interface and calibration
├── vision/           # Object detection (YOLO, mock)
├── tracking/         # Object tracking (IOU, ByteTrack)
├── distance/         # Ultrasonic + monocular distance
├── fusion/           # Sensor/vision fusion
├── ml/               # ML models, training, evaluation
├── acquisition/      # Sensor/frame readers
├── processing/       # Filters, validation, outliers
├── zone/             # Safety engine, state machine
├── alerts/           # LED, buzzer, alert scheduler
├── display/          # LCD, HMI
├── diagnostics/      # Health, metrics, system monitor
├── datalog/          # Event, sensor, vision logging
├── simulation/       # Scenarios, simulator
├── dashboard/        # FastAPI backend + HTML frontend
├── tools/            # Calibration, dataset, benchmark
├── config/           # YAML configuration files
├── tests/            # Unit, integration, simulation tests
├── models/           # Model weights (not committed)
├── data/             # Datasets, recordings
├── docs/             # Documentation
└── logs/             # Runtime logs
```

---

## 13. Known Limitations

- **Prototype values** — all safety thresholds are initial/demo values
- **No production safety certification** — not ISO 26262 compliant
- **Monocular distance is approximate** — depends on calibration and object size assumptions
- **YOLO weights not committed** — auto-downloaded on first use, falls back to mock
- **Simulation only** — real hardware testing not yet performed on target board
- **No guaranteed FPS** — performance must be measured on target hardware
- **No guaranteed collision prevention** — this is a driver assistance prototype
- **Dashboard is monitoring-only** — never replaces the safety engine

---

## 14. License

MIT License — See LICENSE file for details.
