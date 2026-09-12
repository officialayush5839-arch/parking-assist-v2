#!/usr/bin/env bash
echo "KPIT Parking Assist V2.0 - Demo Mode"
echo "====================================="
python3 -m app.main --mode demo --dashboard "$@"
