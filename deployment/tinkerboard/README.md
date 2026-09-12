# KPIT Parking Assist V2.0 — ASUS Tinker Board Deployment

## Quick Start

### 1. Install on Tinker Board

```bash
cd /opt/parking_assist_v2
sudo bash deployment/tinkerboard/install.sh
```

### 2. Start the Service

```bash
sudo systemctl start parking-assist
```

### 3. Check Status

```bash
sudo systemctl status parking-assist
```

### 4. Access Dashboard from Laptop

Open browser and navigate to:

```
http://<TINKER_BOARD_IP>:8765
```

### 5. View Logs

```bash
sudo journalctl -u parking-assist -f
```

## Service Management

```bash
# Start
sudo systemctl start parking-assist

# Stop
sudo systemctl stop parking-assist

# Restart
sudo systemctl restart parking-assist

# Status
sudo systemctl status parking-assist

# Logs
sudo journalctl -u parking-assist -f

# Enable on boot
sudo systemctl enable parking-assist

# Disable on boot
sudo systemctl disable parking-assist
```

## Scripts

```bash
# Start (manual)
bash deployment/tinkerboard/start.sh

# Stop (manual)
bash deployment/tinkerboard/stop.sh

# Status
bash deployment/tinkerboard/status.sh
```

## Health Check

```bash
# Run comprehensive health check
python -m tools.health_check

# Run hardware self-test
python -m tools.hardware_test

# Run camera test
python -m tools.camera_test

# Run sensor test
python -m tools.hardware_test --sensor-only
```

## Configuration

Edit files in `config/`:

- `config.yaml` — Main configuration
- `safety.yaml` — Safety zones and thresholds
- `camera.yaml` — Camera settings
- `logging.yaml` — Logging configuration

## Network Access

The dashboard binds to `0.0.0.0:8765` by default when `--dashboard` is used.

From your laptop:

```bash
# Find Tinker Board IP
ip addr show

# Test connectivity
ping <LAPTOP_IP>

# Open dashboard
http://<TINKER_BOARD_IP>:8765
```

## Troubleshooting

See `docs/TROUBLESHOOTING.md` for detailed troubleshooting guide.
