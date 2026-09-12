# KPIT Parking Assist V2.0 — Dependency Compatibility for ASUS Tinker Board

**Target Hardware:** ASUS Tinker Board R2.0  
**Target OS:** Debian-based Linux (ARMHF/ARM64)  
**Python Version:** 3.10+ (recommend 3.10 for best ARM compatibility)  

---

## 1. Dependency Compatibility Matrix

| Package | Version | Windows | Linux x86_64 | Linux ARM (Tinker Board) | Notes |
|---------|---------|---------|--------------|--------------------------|-------|
| **Core** | | | | | |
| numpy | >=1.24 | ✓ | ✓ | ✓ | Wheels available for ARM |
| PyYAML | >=6.0 | ✓ | ✓ | ✓ | Pure Python |
| psutil | >=5.9 | ✓ | ✓ | ✓ | Wheels for ARM |
| **Vision** | | | | | |
| opencv-python | >=4.5 | ✓ | ✓ | ⚠ | Use opencv-python-headless on server; ARM wheels available but large |
| ultralytics | >=8.0 | ✓ | ✓ | ⚠ | PyTorch dependency; CPU-only on Tinker Board |
| **ML** | | | | | |
| scikit-learn | >=1.3 | ✓ | ✓ | ✓ | Wheels for ARM; CPU inference only |
| **Dashboard** | | | | | |
| fastapi | >=0.110 | ✓ | ✓ | ✓ | Pure Python |
| uvicorn | >=0.27 | ✓ | ✓ | ✓ | Pure Python |
| **Hardware** | | | | | |
| smbus2 | >=0.4 | N/A | ✓ | ✓ | I2C on Linux only |
| RPLCD | >=1.4 | N/A | ✓ | ✓ | I2C LCD on Linux only |
| RPi.GPIO | — | N/A | ⚠ | ⚠ | **NOT compatible with Tinker Board** — Use Tinker Board SDK |
| tinker-board-sdk | — | N/A | N/A | ✓ | Required for GPIO on Tinker Board |
| **Testing** | | | | | |
| pytest | >=7.4 | ✓ | ✓ | ✓ | Pure Python |

---

## 2. Critical Compatibility Notes

### PyTorch/Ultralytics on ARM

**Current Status:** ⚠ POTENTIALLY PROBLEMATIC

PyTorch has limited ARM support:
- PyTorch provides ARM wheels for aarch64 (ARM64)
- Tinker Board R2.0 uses Rockchip RK3399 (ARMv8/AArch64) — should be compatible
- Performance will be significantly lower than x86 GPU systems
- CPU-only inference expected: ~2-5 FPS for YOLOv8n on RK3399

**Recommendation:**
```bash
# On Tinker Board, install CPU-only PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install ultralytics
```

### OpenCV on ARM

**Current Status:** ✓ COMPATIBLE

- opencv-python provides ARM wheels
- For headless operation (no GUI), use opencv-python-headless (smaller, faster)
- MIPI CSI camera support requires additional setup (libcamera or rkmpp)

### GPIO Libraries on Tinker Board

**Current Status:** ⚠ REQUIRES SPECIAL HANDLING

**RPi.GPIO is NOT compatible with Tinker Board.** The Tinker Board has different GPIO hardware.

**Options:**
1. **Tinker Board SDK** (preferred) — Official ASUS GPIO library
2. **libgpiod** — Modern Linux GPIO interface
3. **RPi.GPIO compatible forks** — Some community ports exist but unreliable

**Current Code Issue:** `distance/ultrasonic.py` attempts to import RPi.GPIO first, then tinker_board_sdk. This order should be reversed for Tinker Board deployment.

---

## 3. Recommended Python Version

**Current Requirement:** >=3.10

**Recommendation for Tinker Board:** Python 3.10

**Rationale:**
- Python 3.10 has excellent ARMHF/ARM64 support
- Most dependencies have stable wheels for 3.10
- Avoids potential issues with newer Python versions on older Debian releases
- Tinker Board OS images often ship with Python 3.9-3.11

---

## 4. Dependency Groups for Deployment

### REQUIRED (Core Functionality)
```txt
# requirements-core.txt
numpy>=1.24
PyYAML>=6.0
psutil>=5.9
```

### VISION (For Real Detection)
```txt
# requirements-vision.txt
opencv-python-headless>=4.5
ultralytics>=8.0
```

### ML (For Risk Models)
```txt
# requirements-ml.txt
scikit-learn>=1.3
joblib>=1.3
```

### DASHBOARD (For Web UI)
```txt
# requirements-dashboard.txt
fastapi>=0.110
uvicorn>=0.27
```

### HARDWARE (Tinker Board Only)
```txt
# requirements-hardware.txt
smbus2>=0.4
RPLCD>=1.4
# GPIO: install Tinker Board SDK separately
```

### COMPLETE (All Optional)
```txt
# requirements-arm.txt (for Tinker Board)
numpy>=1.24
PyYAML>=6.0
psutil>=5.9
opencv-python-headless>=4.5
ultralytics>=8.0
scikit-learn>=1.3
joblib>=1.3
fastapi>=0.110
uvicorn>=0.27
smbus2>=0.4
RPLCD>=1.4
pytest>=7.4
```

---

## 5. Packages Requiring Special Attention

### Compilation Required
- None in standard dependencies (all have wheels)

### GPU/CUDA Required
- None (project uses CPU-only inference)

### Special Hardware Required
- GPIO libraries require Tinker Board hardware
- I2C libraries require I2C peripherals connected

### ARM-Specific Issues
- PyTorch CPU performance on RK3399 will be modest
- Consider TFLite for better ARM performance if YOLOv8n is too slow
- opencv-python-headless recommended over opencv-python for headless operation

---

## 6. Installation Sequence for Tinker Board

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install system dependencies
sudo apt install -y python3 python3-pip python3-venv \
    i2c-tools libi2c-dev \
    git vim

# 3. Enable I2C interface
sudo nano /etc/modprobe.d/i2c.conf  # Add: i2c-dev
sudo reboot

# 4. Create virtual environment
python3 -m venv /opt/parking_assist/venv
source /opt/parking_assist/venv/bin/activate

# 5. Install Python dependencies
pip install --upgrade pip
pip install -r requirements-arm.txt

# 6. Install Tinker Board GPIO SDK
# (Download from ASUS or use libgpiod)

# 7. Verify installations
python -c "import numpy, yaml, psutil, cv2; print('Core OK')"
python -c "import ultralytics; print('Vision OK')"
python -c "import sklearn; print('ML OK')"
python -c "import fastapi, uvicorn; print('Dashboard OK')"
```

---

## 7. Alternative: TFLite for Better ARM Performance

If YOLOv8n via PyTorch is too slow on Tinker Board, consider:

**Option A: TFLite Runtime**
```bash
pip install tflite-runtime
# Download EfficientNet-Lite0 or YOLO-TFLite model
python -m tools.fetch_tflite_model
```

**Option B: ONNX Runtime**
```bash
pip install onnxruntime
# Export YOLOv8n to ONNX
```

**Benefits:**
- Better ARM CPU performance
- Smaller memory footprint
- No PyTorch dependency

**Tradeoffs:**
- Requires model conversion
- Slightly different API
- Must verify accuracy is preserved

---

## 8. Dependency Status Summary

| Category | Status |
|----------|--------|
| Core dependencies | ✓ VERIFIED — All compatible with ARM |
| Vision dependencies | ⚠ COMPATIBLE BUT PERFORMANCE CONCERN — PyTorch on ARM |
| ML dependencies | ✓ VERIFIED — scikit-learn works on ARM |
| Dashboard dependencies | ✓ VERIFIED — Pure Python, no issues |
| Hardware dependencies | ⚠ REQUIRES TINKER BOARD SDK — RPi.GPIO incompatible |
| Testing dependencies | ✓ VERIFIED — pytest works on ARM |

---

**Conclusion:** The project's dependencies are generally compatible with ASUS Tinker Board, with the main concerns being:
1. PyTorch/ultralytics performance on ARM CPU
2. GPIO library compatibility (must use Tinker Board SDK, not RPi.GPIO)
3. Consider TFLite as alternative for better performance
