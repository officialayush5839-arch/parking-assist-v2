# Changelog

All notable changes to KPIT Parking Assist V2.0 are documented here.

## [2.0.0] — 2026-09-12

### Added
- Full pipeline: preprocess → detect → track → distance → fusion → TTC → risk → safety
- Deterministic safety engine with hard safety override
- Safety state machine with anti-flicker hysteresis
- IOU-based object tracker with lifecycle management
- Monocular distance estimation (pinhole geometry)
- Sensor/vision confidence fusion with disagreement detection
- Deterministic TTC (time-to-collision) calculation
- Advisory risk scoring (deterministic kinematic + ML stub)
- FastAPI dashboard with WebSocket telemetry stream
- LED alert system (green/yellow/orange/red/blue)
- Buzzer alert patterns per safety zone
- LCD display controller (mock + I2C HD44780)
- Health monitoring system with component tracking
- Performance metrics collector (FPS, latency, per-stage timing)
- System monitor (CPU, RAM, temperature)
- Event bus with publish/subscribe architecture
- JSONL logging (events, sensors, vision, experiments)
- Simulation engine with parameterised scenarios
- Multiple camera backends (USB, MIPI CSI, video file, mock)
- Ultrasonic sensor backend (GPIO, mock, recorded)
- YOLOv8n detection backend (ultralytics)
- TFLite detection backend (EfficientDet-Lite0)
- ByteTrack tracking backend (stub, falls back to IOU)
- ML risk prediction backend (sklearn/joblib stub)
- Anomaly detection (Isolation Forest, disabled by default)
- Configuration system (YAML + env vars + defaults)
- Environment variable overrides (KPA_*)
- Camera calibration system
- Data collection tools
- Dataset pipeline
- ML training scripts
- Model evaluation scripts
- Hardware test tools
- Camera test tool
- Health check tool
- Benchmark tool
- Tinker Board deployment scripts
- Systemd service file
- Self-test mode
- Diagnostics mode

### Safety
- Hard safety override: ultrasonic ≤ critical_threshold → CRITICAL regardless of vision/ML
- State machine: escalation immediate, recovery requires stability_frames persistence
- FAULT when no valid distance source
- Sensor disagreement detection with conservative handling
- ML risk is advisory only — never overrides hard safety

### Testing
- 86 tests (unit, integration, simulation, performance)
- Hard safety override integration tests
- Failure scenario tests (camera/sensor/both invalid)
- State machine tests
- Fusion tests
- TTC tests
- Safety engine tests
- All tests passing

### Known Limitations
- No physical Tinker Board testing yet
- No camera calibration data
- No YOLO model weights downloaded
- No TFLite model weights downloaded
- ByteTrack backend not wired
- ML risk model not trained
- GPIO libraries not installed (Tinker Board SDK required)
- Monocular distance is approximate without calibration
