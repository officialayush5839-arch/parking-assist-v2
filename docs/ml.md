# ML Components

## Overview

ML components are ADVISORY — they never directly control safety hardware.

## Object Detection

- **Backend**: YOLOv8n (ultralytics)
- **Input**: 640x480 frames
- **Classes**: person, car, truck, bus, motorcycle, bicycle, suitcase
- **Fallback**: MockDetector when weights unavailable

## Risk Prediction

- **Interface**: `RiskPredictor.predict(features) -> RiskAssessment`
- **Backends**: DeterministicTTCPredictor, MLRiskPredictor, MockRiskPredictor
- **Output**: risk_score (0-1), risk_class (LOW/MEDIUM/HIGH), confidence
- **Usage**: Reason codes attached to safety decision, never changes state

## Anomaly Detection

- **Purpose**: Diagnostics support (optional)
- **Algorithm**: Isolation Forest
- **Features**: distance, FPS, latency, confidence, CPU, RAM
- **Usage**: System health monitoring, NOT safety-critical

## Training Data Requirements

### Detection Dataset
- Images with bounding box annotations (COCO format)
- Classes: person, car, truck, bus, motorcycle, bicycle
- Environmental variation: daylight, low light, shadows, angles

### Distance Dataset
- Image frames with ground-truth distances
- Paired ultrasonic + camera measurements
- Various object sizes and distances

### Trajectory Dataset
- Time-series of (timestamp, distance, velocity)
- Multiple approach scenarios

### Fault Dataset
- Sensor timeout recordings
- Camera failure recordings
- Sensor disagreement recordings

## Training

```bash
python -m ml.training.train_risk_model --data data/processed/risk_features.csv
python -m ml.training.train_anomaly_model
```

## Evaluation

```bash
python -m ml.evaluation.evaluate_detector --data data/processed/
python -m ml.evaluation.evaluate_distance --data data/processed/
python -m ml.evaluation.evaluate_risk --data data/processed/
```
