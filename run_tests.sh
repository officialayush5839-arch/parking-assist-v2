#!/usr/bin/env bash
echo "KPIT Parking Assist V2.0 - Running Tests"
echo "========================================="
python3 -m pytest --import-mode=importlib -q "$@"
