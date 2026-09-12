# Deployment Guide

## Development (Windows/Linux PC)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run simulation:
   ```bash
   python -m app.main --mode simulation
   ```

3. Run self-test:
   ```bash
   python -m app.main --mode selftest
   ```

## Tinker Board Deployment

### Prerequisites
- Debian-based OS on MicroSD
- Python 3.10+
- Camera driver installed
- I2C enabled for LCD
- GPIO access configured

### Steps

1. Clone/copy project to board
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install smbus2 RPLCD   # hardware extras
   ```
3. Configure `config/config.yaml` for hardware mode
4. Calibrate camera: `python -m tools.calibrate_camera`
5. Run: `python -m app.main --mode hardware`

### Systemd Service (optional)

```ini
[Unit]
Description=KPIT Parking Assist V2.0
After=multi-user.target

[Service]
Type=simple
WorkingDirectory=/opt/parking_assist_v2
ExecStart=/usr/bin/python3 -m app.main --mode hardware
Restart=always

[Install]
WantedBy=multi-user.target
```

## CI/CD Testing

```bash
# In CI environment (no hardware)
python -m pytest --import-mode=importlib -q
python -m app.main --mode selftest
python -m app.main --mode simulation --scenario critical_distance
```

## Known Limitations

- Performance must be measured on target hardware
- Camera calibration required for accurate distance
- Model weights auto-downloaded on first run
- Dashboard requires network access
- All safety thresholds are prototype values
