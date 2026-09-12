#!/usr/bin/env bash
echo "KPIT Parking Assist V2.0 - Simulation Mode"
echo "============================================"
python3 -m app.main --mode simulation "$@"
