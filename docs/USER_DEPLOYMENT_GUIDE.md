# KPIT Parking Assist V2.0 — User Deployment Guide

This guide walks you through deploying the parking assist system on an ASUS Tinker Board and monitoring it from a laptop.

---

## Overview

```
                    ┌─────────────────────┐
                    │     LAPTOP          │
                    │                     │
                    │ Browser             │
                    │ Dashboard           │
                    └─────────┬───────────┘
                              │
                     Ethernet / Wi-Fi
                              │
                              ▼
                    ┌─────────────────────┐
                    │ ASUS TINKER BOARD   │
                    │                     │
                    │ Parking Assist App  │
                    │ FastAPI             │
                    │ WebSocket           │
                    │ Camera              │
                    │ Ultrasonic          │
                    │ ML Models           │
                    │ Safety Engine       │
                    │ LCD/LED/Buzzer      │
                    └─────────────────────┘
```

---

## Step 1 — Prepare SD Card

### Recommended OS

- **TinkerOS (Debian-based)** — Official ASUS image
- **Armbian** — Community-maintained, good support
- **Ubuntu Server for ARM** — Alternative option

### SD Card Preparation

1. Download the OS image for your Tinker Board model
2. Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) or [balenaEtcher](https://etcher.balena.io/) to flash the image to an SD card (minimum 16GB recommended)
3. Insert SD card into Tinker Board
4. Connect power, HDMI (optional), Ethernet

### First Boot

1. Connect Tinker Board to power
2. Wait for boot (green LED activity)
3. Connect to Tinker Board via SSH or monitor

---

## Step 2 — Connect Hardware

### Hardware Connection Table

| Component | Connection | Notes |
|-----------|-----------|-------|
| Power | 5V/3A USB-C or barrel jack | Use official power supply |
| HDMI | Micro HDMI | Optional, for initial setup |
| Ethernet | RJ-45 | Recommended for first deployment |
| Camera | USB or MIPI CSI | USB: plug into USB port; MIPI: connect to camera port |
| Ultrasonic | GPIO pins | See pin mapping below |
| LCD | I2C | SDA/SCL pins |
| LEDs | GPIO pins | Via MOSFET drivers |
| Buzzer | GPIO pin | Via MOSFET driver |

### GPIO Pin Mapping (Default)

| Pin | Function | GPIO | Notes |
|-----|----------|------|-------|
| Trigger | Ultrasonic | GPIO17 | Output |
| Echo | Ultrasonic | GPIO27 | Input |
| SDA | I2C LCD | GPIO0 | I2C |
| SCL | I2C LCD | GPIO1 | I2C |
| LED Green | Status | GPIO5 | Output via MOSFET |
| LED Yellow | Status | GPIO6 | Output via MOSFET |
| LED Orange | Status | GPIO13 | Output via MOSFET |
| LED Red | Status | GPIO19 | Output via MOSFET |
| LED Blue | Status | GPIO26 | Output via MOSFET |
| Buzzer | Alert | GPIO21 | Output via MOSFET |

⚠ **REQUIRES PHYSICAL VERIFICATION** — Pin mappings must be verified against your specific Tinker Board model and hardware configuration.

### Voltage Requirements

- Tinker Board GPIO: 3.3V logic level
- LEDs: Use MOSFET drivers for 5V LEDs
- Buzzer: Use MOSFET driver for 5V buzzer
- Ultrasonic: 5V VCC, 3.3V logic

---

## Step 3 — Connect Tinker Board to Laptop

### Option A — Ethernet (Recommended for First Deployment)

1. Connect Ethernet cable between Tinker Board and router/switch
2. Connect laptop to same network
3. Find Tinker Board IP address (see below)

### Option B — Same Wi-Fi Network

1. Configure Wi-Fi on Tinker Board
2. Connect laptop to same Wi-Fi network
3. Find Tinker Board IP address

### Option C — Direct Ethernet

1. Connect Ethernet cable directly between Tinker Board and laptop
2. Configure static IPs:
   - Tinker Board: `192.168.1.10/24`
   - Laptop: `192.168.1.20/24`
3. No router needed

### Finding IP Address

```bash
# On Tinker Board
ip addr show

# From laptop (Linux/macOS)
arp -a | grep tinker

# From laptop (Windows)
arp -a

# From laptop (scan network)
nmap -sn 192.168.1.0/24
```

### Testing Connectivity

```bash
# From laptop
ping <TINKER_BOARD_IP>
```

---

## Step 4 — Install Application

### On Tinker Board

```bash
# SSH into Tinker Board
ssh <USERNAME>@<TINKER_BOARD_IP>

# Clone or copy the project
cd /opt
git clone <REPO_URL> parking_assist_v2
# OR copy from USB drive

# Run installation
cd parking_assist_v2
sudo bash deployment/tinkerboard/install.sh
```

### What the Installer Does

1. Creates `/opt/parking_assist_v2` directory
2. Sets up Python virtual environment
3. Installs Python dependencies
4. Copies application files
5. Installs systemd service
6. Enables service on boot

---

## Step 5 — Configure Application

### Edit Configuration Files

```bash
cd /opt/parking_assist_v2

# Main configuration
nano config/config.yaml

# Safety zones
nano config/safety.yaml

# Camera settings
nano config/camera.yaml

# Logging
nano config/logging.yaml
```

### Key Configuration Options

```yaml
# config/config.yaml
system:
  mode: hardware          # Use 'hardware' for real deployment
  loop_hz: 15            # Target pipeline rate

vision:
  backend: auto          # auto | yolo | tflite | mock
  model: yolov8n
  confidence_threshold: 0.40

dashboard:
  host: 0.0.0.0          # Bind to all interfaces for laptop access
  port: 8765
```

---

## Step 6 — Start Application

### Start Service

```bash
# Start the parking assist service
sudo systemctl start parking-assist

# Check status
sudo systemctl status parking-assist

# Enable on boot
sudo systemctl enable parking-assist
```

### Manual Start (Alternative)

```bash
# Start with dashboard
python -m app.main --mode hardware --dashboard

# Start in simulation mode (for testing)
python -m app.main --mode simulation --dashboard
```

---

## Step 7 — Access Dashboard from Laptop

### Open Browser

Navigate to:

```
http://<TINKER_BOARD_IP>:8765
```

### Dashboard Features

- **Safety State** — Current safety zone (SAFE/CAUTION/WARNING/CRITICAL/FAULT)
- **Distance** — Object distance in meters
- **Object** — Detected object class
- **Confidence** — Detection confidence percentage
- **Closing Speed** — Approach speed in m/s
- **TTC** — Time to collision in seconds
- **Risk Score** — Risk percentage
- **FPS** — Current frames per second
- **Latency** — Pipeline latency in ms
- **Events** — Recent system events
- **Health** — Component health status

---

## Step 8 — Verify Operation

### Run Health Check

```bash
# On Tinker Board
python -m tools.health_check --verbose
```

Expected output:
```
KPIT PARKING ASSIST V2 HEALTH CHECK
================================================================

  [PASS] Operating System
  [PASS] Python
  [PASS] CPU
  [PASS] RAM
  [PASS] Storage
  [PASS] Temperature
  [PASS] Camera
  [PASS] Ultrasonic
  [PASS] LCD
  [PASS] LED GPIO
  [PASS] Buzzer GPIO
  [PASS] Detector
  [PASS] Tracker
  [PASS] Distance Estimator
  [PASS] Fusion
  [PASS] Risk Model
  [PASS] Safety Engine
  [PASS] Dashboard
  [PASS] Network
  [PASS] Configuration

================================================================
RESULT: READY
================================================================
```

### Run Hardware Self-Test

```bash
python -m tools.hardware_test --output logs/hardware_self_test.json
```

---

## SSH Access

### Windows (PowerShell)

```powershell
ssh <USERNAME>@<TINKER_BOARD_IP>
```

### Linux/macOS

```bash
ssh <USERNAME>@<TINKER_BOARD_IP>
```

### Useful Commands

```bash
# Check service status
sudo systemctl status parking-assist

# View logs
sudo journalctl -u parking-assist -f

# Restart service
sudo systemctl restart parking-assist

# Stop service
sudo systemctl stop parking-assist

# Check system resources
htop

# Check temperature
cat /sys/class/thermal/thermal_zone0/temp
```

---

## Offline Operation

After installation, the Tinker Board runs the core system without internet:

✅ **Works Offline:**
- Camera capture
- Object detection
- Object tracking
- Distance estimation
- Sensor fusion
- Risk calculation
- Safety engine
- LCD display
- LED alerts
- Buzzer alerts
- Local dashboard

❌ **Requires Internet:**
- Initial package installation
- Optional model download
- System updates

---

## Next Steps

1. Calibrate camera: `python -m tools.calibrate_camera`
2. Download model weights: `python -m tools.fetch_yolo_weights`
3. Run performance benchmark: `python -m tools.benchmark`
4. Test hardware components: `python -m tools.hardware_test`
5. Review troubleshooting guide: `docs/TROUBLESHOOTING.md`
