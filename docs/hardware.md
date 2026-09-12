# Hardware Deployment Guide

## Target Hardware

- **Board**: ASUS Tinker Board R2.0 (or compatible)
- **OS**: Debian-based Linux
- **Storage**: MicroSD (32GB+ recommended)
- **Power**: 5V/3A regulated supply

## Components

| Component | Interface | GPIO/Pin |
|---|---|---|
| MIPI CSI Camera | CSI connector | — |
| JSN-SR04T Ultrasonic | GPIO (trigger/echo) | GPIO17 (trigger), GPIO27 (echo) |
| 20x4 I2C LCD | I2C (SDA/SCL) | I2C bus 1 |
| Green LED | GPIO | GPIO22 |
| Yellow LED | GPIO | GPIO23 |
| Orange LED | GPIO | GPIO24 |
| Red LED | GPIO | GPIO25 |
| Blue LED | GPIO | GPIO26 |
| 5V Buzzer | GPIO (via MOSFET) | GPIO5 |

## Wiring Notes

- Use logic-level converters between 3.3V GPIO and 5V peripherals
- MOSFET drivers recommended for buzzer and LED arrays
- Heatsink/fan recommended for continuous operation
- Decoupling capacitors on power rails

## Configuration

Edit `config/config.yaml`:

```yaml
hardware:
  camera: mipi
  distance_sensor: real
  lcd: i2c
  leds: gpio
  buzzer: gpio
  distance:
    ultrasonic:
      trigger_pin: 17
      echo_pin: 27
```

## Camera Calibration

Before deployment, calibrate the camera:

```bash
python -m tools.calibrate_camera
```

This outputs `config/camera_calibration.yaml` with intrinsic parameters.

## Safety Thresholds

⚠️ All thresholds in `config/safety.yaml` are DEMO values. They MUST be experimentally validated for your specific vehicle, sensor placement, and braking characteristics before any real-world use.
