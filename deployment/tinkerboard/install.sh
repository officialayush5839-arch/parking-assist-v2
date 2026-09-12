#!/bin/bash
# deployment/tinkerboard/install.sh
# KPIT Parking Assist V2.0 — Tinker Board installation script
#
# Usage: sudo bash install.sh
#
# This script installs the parking assist application on an ASUS Tinker Board.

set -e

echo "=============================================="
echo "KPIT Parking Assist V2.0 — Installation"
echo "=============================================="
echo

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "WARNING: Not running as root. Some operations may fail."
    echo "Consider running with: sudo bash install.sh"
    echo
fi

# Configuration
APP_NAME="parking_assist_v2"
APP_DIR="/opt/${APP_NAME}"
VENV_DIR="${APP_DIR}/venv"
USER="${SUDO_USER:-pi}"
GROUP="${USER}"

echo "[1/8] Creating application directory..."
mkdir -p "${APP_DIR}"
chmod 755 "${APP_DIR}"

echo "[2/8] Creating system user (if needed)..."
if ! id -u "${USER}" >/dev/null 2>&1; then
    useradd --system --create-home --shell /bin/bash "${USER}"
    echo "  Created user: ${USER}"
else
    echo "  User exists: ${USER}"
fi

echo "[3/8] Setting up Python virtual environment..."
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
    echo "  Created venv: ${VENV_DIR}"
else
    echo "  Venv exists: ${VENV_DIR}"
fi

echo "[4/8] Installing Python dependencies..."
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements/requirements-arm.txt"

echo "[5/8] Copying application files..."
# Copy application (excluding dev/test files)
cp -r app "${APP_DIR}/"
cp -r camera "${APP_DIR}/"
cp -r vision "${APP_DIR}/"
cp -r tracking "${APP_DIR}/"
cp -r distance "${APP_DIR}/"
cp -r fusion "${APP_DIR}/"
cp -r ml "${APP_DIR}/"
cp -r acquisition "${APP_DIR}/"
cp -r processing "${APP_DIR}/"
cp -r zone "${APP_DIR}/"
cp -r alerts "${APP_DIR}/"
cp -r display "${APP_DIR}/"
cp -r diagnostics "${APP_DIR}/"
cp -r datalog "${APP_DIR}/"
cp -r simulation "${APP_DIR}/"
cp -r dashboard "${APP_DIR}/"
cp -r tools "${APP_DIR}/"
cp -r config "${APP_DIR}/"
cp "deployment/tinkerboard/parking-assist.service" "/etc/systemd/system/"
cp "deployment/tinkerboard/README.md" "${APP_DIR}/"
cp "VERSION" "${APP_DIR}/" 2>/dev/null || echo "2.0.0" > "${APP_DIR}/VERSION"
cp "CHANGELOG.md" "${APP_DIR}/" 2>/dev/null || true
cp "RELEASE_NOTES.md" "${APP_DIR}/" 2>/dev/null || true

echo "[6/8] Setting permissions..."
chown -R "${USER}:${GROUP}" "${APP_DIR}"
chmod +x "${APP_DIR}/tools/"*.py 2>/dev/null || true

echo "[7/8] Enabling systemd service..."
systemctl daemon-reload
systemctl enable parking-assist.service

echo "[8/8] Installation complete!"
echo
echo "=============================================="
echo "Installation Summary"
echo "=============================================="
echo "Application directory: ${APP_DIR}"
echo "Virtual environment:   ${VENV_DIR}"
echo "Service:               parking-assist"
echo
echo "Next steps:"
echo "  1. Configure hardware in ${APP_DIR}/config/"
echo "  2. Calibrate camera: sudo -u ${USER} ${VENV_DIR}/bin/python -m tools.calibrate_camera"
echo "  3. Start service:   sudo systemctl start parking-assist"
echo "  4. Check status:    sudo systemctl status parking-assist"
echo "  5. View logs:       sudo journalctl -u parking-assist -f"
echo
echo "Dashboard will be available at: http://<TINKER_BOARD_IP>:8765"
echo
