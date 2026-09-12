# KPIT Parking Assist V2.0 — Troubleshooting Guide

## Dashboard Doesn't Open

### Checklist

1. **Tinker Board powered on**
   ```bash
   ping <TINKER_BOARD_IP>
   ```

2. **Network connected**
   ```bash
   ip addr show
   ```

3. **Service running**
   ```bash
   sudo systemctl status parking-assist
   ```

4. **Port listening**
   ```bash
   ss -tlnp | grep 8765
   ```

5. **Firewall**
   ```bash
   sudo iptables -L -n | grep 8765
   ```

6. **Correct IP**
   - Dashboard URL: `http://<TINKER_BOARD_IP>:8765`
   - Not `localhost` or `127.0.0.1` from the laptop

### Common Fixes

```bash
# Restart service
sudo systemctl restart parking-assist

# Check logs
sudo journalctl -u parking-assist -f

# Check if port is blocked
sudo ufw allow 8765/tcp
```

---

## Camera Doesn't Work

### Checklist

1. **Camera connection**
   ```bash
   ls /dev/video*
   ```

2. **Camera permissions**
   ```bash
   sudo usermod -a -G video $USER
   ```

3. **Camera test**
   ```bash
   python -m tools.camera_test --backend usb
   ```

4. **MIPI CSI camera**
   ```bash
   # Check if camera is detected
   v4l2-ctl --list-devices
   ```

5. **Camera backend**
   ```bash
   # Check config
   cat config/camera.yaml
   ```

### Common Fixes

```bash
# Use mock camera for testing
# Set in config/camera.yaml:
#   camera.backend: mock

# Test with video file
python -m tools.camera_test --backend video --video-file path/to/video.mp4
```

---

## Ultrasonic Sensor Doesn't Work

### Checklist

1. **Wiring**
   - Trigger pin → GPIO pin (default: GPIO17)
   - Echo pin → GPIO pin (default: GPIO27)
   - VCC → 5V
   - GND → GND

2. **GPIO permissions**
   ```bash
   sudo usermod -a -G gpio $USER
   ```

3. **Sensor test**
   ```bash
   python -m tools.hardware_test --sensor-only
   ```

4. **GPIO library**
   ```bash
   # Check if GPIO library is available
   python -c "import RPi.GPIO; print('RPi.GPIO OK')"
   # OR
   python -c "import tinker_board_sdk; print('Tinker Board SDK OK')"
   ```

### Common Fixes

```bash
# Use mock sensor for testing
# Set in config/config.yaml:
#   distance.ultrasonic.backend: mock

# Check GPIO pins
gpio readall
```

---

## Model Doesn't Load

### Checklist

1. **Weights path**
   ```bash
   ls models/detector/
   ```

2. **Download weights**
   ```bash
   python -m tools.fetch_yolo_weights
   ```

3. **Model runtime**
   ```bash
   # Check ultralytics
   python -c "from ultralytics import YOLO; print('ultralytics OK')"
   ```

4. **Dependencies**
   ```bash
   pip list | grep ultralytics
   pip list | grep torch
   ```

5. **RAM**
   ```bash
   free -h
   ```

### Common Fixes

```bash
# Download YOLOv8n weights
python -m tools.fetch_yolo_weights

# Or use mock detector
# Set in config/config.yaml:
#   vision.backend: mock
```

---

## System Is Slow

### Checklist

1. **Model size**
   ```bash
   # Check model size
   ls -lh models/detector/*.pt
   ```

2. **Input resolution**
   ```bash
   # Check config
   cat config/config.yaml | grep input_width
   ```

3. **FPS**
   ```bash
   # Run benchmark
   python -m tools.benchmark --frames 100
   ```

4. **CPU usage**
   ```bash
   top -bn1 | head -20
   ```

5. **Thermal throttling**
   ```bash
   cat /sys/class/thermal/thermal_zone0/temp
   ```

6. **Background processes**
   ```bash
   ps aux | grep python
   ```

### Common Fixes

```bash
# Reduce loop rate
# Set in config/config.yaml:
#   system.loop_hz: 10

# Use smaller model
# Set in config/config.yaml:
#   vision.model: yolov8n

# Reduce input resolution
# Set in config/config.yaml:
#   vision.input_width: 320
#   vision.input_height: 240
```

---

## Dashboard Works But Hardware Does Not

### Isolation Steps

1. **Dashboard only**
   ```bash
   python -m app.main --mode simulation --dashboard
   ```

2. **Camera mode**
   ```bash
   python -m app.main --mode camera --dashboard
   ```

3. **Hardware mode**
   ```bash
   python -m app.main --mode hardware --dashboard
   ```

4. **Check component health**
   ```bash
   curl http://localhost:8765/api/health
   ```

5. **Check logs**
   ```bash
   tail -f logs/events.jsonl
   ```

---

## Python Import Errors

### Common Errors

```bash
# ModuleNotFoundError: No module named 'cv2'
pip install opencv-python-headless

# ModuleNotFoundError: No module named 'ultralytics'
pip install ultralytics

# ModuleNotFoundError: No module named 'RPi.GPIO'
# This is expected on non-Raspberry Pi systems
# Use mock backends instead

# ModuleNotFoundError: No module named 'fastapi'
pip install fastapi uvicorn
```

---

## Network Issues

### Finding Tinker Board IP

```bash
# On Tinker Board
ip addr show

# From laptop
arp -a | grep tinker
nmap -sn 192.168.1.0/24
```

### Testing Connectivity

```bash
# From laptop
ping <TINKER_BOARD_IP>
telnet <TINKER_BOARD_IP> 8765

# On Tinker Board
curl http://localhost:8765/api/health
```

### SSH Access

```bash
# From laptop
ssh <USERNAME>@<TINKER_BOARD_IP>

# Default credentials vary by OS image
# Check your Tinker Board OS documentation
```

---

## Log Files

```bash
# Event logs
tail -f logs/events.jsonl

# Sensor logs
tail -f logs/sensor.jsonl

# Vision logs
tail -f logs/vision.jsonl

# Experiment logs
tail -f logs/experiment.jsonl
```

---

## Getting Help

1. Run health check: `python -m tools.health_check --verbose`
2. Run hardware test: `python -m tools.hardware_test`
3. Check logs: `tail -f logs/events.jsonl`
4. Check systemd: `sudo journalctl -u parking-assist -f`
5. Check service: `sudo systemctl status parking-assist`
