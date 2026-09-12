#!/bin/bash
# deployment/tinkerboard/status.sh
# KPIT Parking Assist V2.0 — Status script for Tinker Board

APP_DIR="/opt/parking_assist_v2"
VENV_DIR="${APP_DIR}/venv"

echo "=============================================="
echo "KPIT Parking Assist V2.0 — Status"
echo "=============================================="
echo

# Check systemd service
echo "Systemd Service:"
systemctl status parking-assist --no-pager 2>/dev/null || echo "  Service not found or not running"

echo

# Check process
echo "Process:"
pgrep -fa "python.*app.main" || echo "  No running process found"

echo

# Check dashboard
echo "Dashboard:"
curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8765/api/health" 2>/dev/null || echo "  Dashboard not responding"

echo
echo "=============================================="
