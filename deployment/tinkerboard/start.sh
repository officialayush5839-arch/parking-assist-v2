#!/bin/bash
# deployment/tinkerboard/start.sh
# KPIT Parking Assist V2.0 — Start script for Tinker Board

APP_DIR="/opt/parking_assist_v2"
VENV_DIR="${APP_DIR}/venv"

echo "Starting KPIT Parking Assist V2.0..."

# Activate venv and start application
cd "${APP_DIR}"
source "${VENV_DIR}/bin/activate"

python -m app.main --mode hardware --dashboard

deactivate
