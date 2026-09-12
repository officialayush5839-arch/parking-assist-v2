#!/bin/bash
# deployment/tinkerboard/stop.sh
# KPIT Parking Assist V2.0 — Stop script for Tinker Board

APP_DIR="/opt/parking_assist_v2"
VENV_DIR="${APP_DIR}/venv"

echo "Stopping KPIT Parking Assist V2.0..."

# Find and stop any running instance
pkill -f "python -m app.main" 2>/dev/null || true

echo "Stopped."
