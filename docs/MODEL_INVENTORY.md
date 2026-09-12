# KPIT Parking Assist V2.0 — Model Inventory

**Inventory Date:** 2026-09-11  
**Status:** ACCURACY IMPROVEMENT BLOCKED BY DATA AVAILABILITY  

---

## 1. Object Detector

### YOLOv8n (Primary Candidate)

| Property | Value |
|----------|-------|
| **Model Name** | YOLOv8n |
| **Model Type** | Object detection (CNN) |
| **Framework** | Ultralytics (PyTorch) |
| **Version** | Latest stable (via ultralytics>=8.0) |
| **Weights Location** | `models/detector/yolov8n.pt` |
| **Weights Present** | ❌ NO — Must be downloaded |
| **Input Resolution** | 640×480 (configurable, default 640×640 native) |
| **Classes** | person, car, truck, bus, motorcycle, bicycle, suitcase |
| **Training Dataset** | COCO (pre-trained) |
| **Dataset Version** | COCO 2017 |
| **Training Status** | PRE-TRAINED (not fine-tuned for parking) |
| **Validation Status** | ❌ NOT VERIFIED — No weights to test |
| **Precision** | NOT MEASURED |
| **Recall** | NOT MEASURED |
| **F1** | NOT MEASURED |
| **mAP50** | NOT MEASURED |
| **mAP50-95** | NOT MEASURED |
| **Inference Latency** | NOT MEASURED (estimated 50-200ms CPU) |
| **FPS** | NOT MEASURED (estimated 5-20 FPS CPU) |
| **Model Size** | ~6.2 MB (FP32) |
| **CPU Compatibility** | ✅ YES |
| **ARM Compatibility** | ✅ YES (CPU inference) |
| **Quantization Status** | ❌ NOT EVALUATED |
| **Current Production Candidate** | ❌ NO — Using MockDetector |

**Notes:**
- Pre-trained on COCO, not fine-tuned for parking lot scenarios
- May need fine-tuning for optimal parking-assist performance
- Falls back to MockDetector when weights unavailable

---

### TFLite Backend (Alternative)

| Property | Value |
|----------|-------|
| **Model Name** | EfficientDet-Lite0/1/2 or MobileNet-SSD v2 |
| **Model Type** | Object detection |
| **Framework** | TFLite Runtime or TensorFlow |
| **Weights Location** | `models/detector/<model_name>/model.tflite` |
| **Weights Present** | ❌ NO — Must be downloaded |
| **Input Resolution** | Model-dependent (typically 256×256 or 320×320) |
| **Classes** | COCO classes (80 classes) |
| **Training Dataset** | COCO |
| **Validation Status** | ❌ NOT VERIFIED |
| **Inference Latency** | EXPECTED BETTER THAN YOLO ON ARM |
| **Model Size** | ~3-8 MB (varies by model) |
| **ARM Compatibility** | ✅ YES (TFLite optimized for mobile/ARM) |
| **Quantization Status** | ✅ TFLite supports INT8 quantization |
| **Current Production Candidate** | ❌ NO — Not configured as default |

**Notes:**
- ported from v1 tinker-vision-alert project
- Better ARM CPU performance expected than PyTorch YOLOv8n
- Requires separate model download via `tools/fetch_tflite_model.py`

---

## 2. Object Tracker

### IOU Tracker (Current Default)

| Property | Value |
|----------|-------|
| **Type** | Algorithm/Backend (NOT a trained ML model) |
| **Implementation** | IoU-based greedy matching |
| **Configuration** | `tracking.iou_threshold: 0.30`, `tracking.max_lost_frames: 20` |
| **Training Required** | ❌ NO (algorithmic) |
| **Status** | ✅ VERIFIED — Working in tests |

**Classification:** Correctly classified as an algorithm/backend, not a separately trained ML model.

---

### ByteTrack (Optional Upgrade)

| Property | Value |
|----------|-------|
| **Type** | Algorithm/Backend (NOT a trained ML model) |
| **Implementation** | ByteTrack (bytetrack-python or ultralytics) |
| **Status** | ❌ NOT WIRED — Falls back to IOU tracker |
| **Training Required** | ❌ NO (algorithmic) |

**Notes:**
- Better tracking performance expected, especially with occlusion
- Not yet integrated — raises TrackerUnavailable and falls back to IOU
- Would require `pip install bytetrack` or similar

---

## 3. Monocular Distance Estimator

| Property | Value |
|----------|-------|
| **Type** | Geometric (pinhole camera model) — NOT ML |
| **Formula** | `distance = (known_width × focal_length) / bbox_width` |
| **Training** | ❌ NONE REQUIRED |
| **Calibration Required** | ✅ YES — focal_length_px must be calibrated |
| **Calibration File** | `config/camera_calibration.yaml` |
| **Calibration Present** | ❌ NO — File missing |
| **Default Focal Length** | 600.0 px (placeholder) |
| **Known Widths** | person:0.5m, car:1.8m, truck:2.4m, bus:2.5m, motorcycle:0.8m, bicycle:0.6m, suitcase:0.5m |
| **Accuracy** | APPROXIMATE — Depends on calibration and object size assumptions |
| **Confidence Scaling** | Reduced when uncalibrated, truncated bbox, unstable bbox, unknown class |
| **Status** | ✅ IMPLEMENTED — Cannot be accurate without calibration |

**Accuracy Limitations:**
- Requires accurate focal length calibration
- Assumes known object widths (error if object size differs)
- Degraded by occlusion, truncation, perspective
- NOT ground truth — always an estimate

---

## 4. Risk Predictor

### DeterministicTTCPredictor (Current Default)

| Property | Value |
|----------|-------|
| **Type** | Deterministic kinematic (NOT ML) |
| **Formula** | `risk = 0.5×distance_factor + 0.3×speed_factor + 0.2×ttc_factor` |
| **Training** | ❌ NONE REQUIRED |
| **Parameters** | safe_min_m=2.5, high_speed_mps=1.0, ttc_warning_s=3.0 |
| **Output** | risk_score (0-1), risk_class (LOW/MEDIUM/HIGH), confidence |
| **Status** | ✅ ACTIVE — Default backend |

---

### MLRiskPredictor (Optional)

| Property | Value |
|----------|-------|
| **Type** | ML (scikit-learn) |
| **Framework** | joblib/sklearn |
| **Model Path** | `ml/models/risk_model.joblib` |
| **Model Present** | ❌ NO — Must be trained |
| **Training Required** | ✅ YES — Requires dataset |
| **Training Script** | `ml/training/train_risk_model.py` |
| **Training Status** | ❌ NOT TRAINED — No data |
| **Status** | ❌ NOT AVAILABLE — Using deterministic fallback |

---

### MockRiskPredictor (Development Only)

| Property | Value |
|----------|-------|
| **Type** | Mock/Fake (development only) |
| **Output** | Always LOW risk, 0.0 score |
| **Status** | ⚠️ DEVELOPMENT ONLY — Clearly marked |

---

## 5. Anomaly Detection Model

| Property | Value |
|----------|-------|
| **Type** | ML (Isolation Forest) |
| **Framework** | scikit-learn |
| **Purpose** | Diagnostics only (NOT safety-critical) |
| **Enabled** | ❌ FALSE (default) |
| **Training Script** | `ml/training/train_anomaly_model.py` |
| **Status** | ✅ IMPLEMENTED — Disabled by default |

---

## 6. Model Status Summary

| Model | Type | Present | Validated | Production Ready |
|-------|------|---------|-----------|------------------|
| YOLOv8n detector | CNN (PyTorch) | ❌ NO | ❌ NO | ❌ NO (mock fallback) |
| TFLite detector | CNN (TFLite) | ❌ NO | ❌ NO | ❌ NO (not configured) |
| IOU Tracker | Algorithm | ✅ YES | ✅ YES | ✅ YES |
| ByteTrack | Algorithm | ❌ NO | ❌ NO | ❌ NO (not wired) |
| Monocular distance | Geometric | ✅ YES | ❌ NO (no calibration) | ⚠️ APPROXIMATE |
| Deterministic risk | Kinematic | ✅ YES | ✅ YES | ✅ YES (default) |
| ML risk model | ML (sklearn) | ❌ NO | ❌ NO | ❌ NO |
| Anomaly model | ML (Isolation Forest) | ❌ NO | ❌ NO | ❌ NO (disabled) |

---

## 7. Model Improvement Roadmap

### Immediate (No Training Data Required)
1. ✅ Download YOLOv8n weights (pre-trained)
2. ⚠️ Evaluate pre-trained YOLO on parking scenarios
3. ⚠️ Consider TFLite for better ARM performance
4. ⚠️ Calibrate camera for monocular distance

### After Data Collection
5. Collect parking lot images with annotations
6. Fine-tune YOLOv8n on parking data (if needed)
7. Train ML risk predictor on collected data
8. Evaluate and compare models

### Advanced
9. Evaluate quantization (FP16/INT8) for ARM
10. Compare accuracy vs performance tradeoffs
11. Select optimal model for deployment

---

## 8. Current Model State

**DEFAULT OPERATION:** MockDetector + DeterministicTTCPredictor

The system currently runs with:
- **Detection:** MockDetector (simulated detections)
- **Tracking:** IOU Tracker (algorithmic)
- **Distance:** Monocular (uncalibrated, approximate) + Ultrasonic (mock)
- **Risk:** DeterministicTTCPredictor (kinematic, no ML)

**This is acceptable for:**
- ✅ Simulation testing
- ✅ Pipeline validation
- ✅ Safety logic verification
- ✅ Development

**This is NOT acceptable for:**
- ❌ Real hardware deployment
- ❌ Real obstacle detection
- ❌ Production use

---

**Model accuracy improvement is BLOCKED BY DATA AVAILABILITY.** No training dataset exists for parking-specific scenarios. Pre-trained COCO models may work but must be evaluated before deployment.
