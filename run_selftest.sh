#!/usr/bin/env bash
echo "KPIT Parking Assist V2.0 - Self Test"
echo "====================================="
python3 -m app.main --mode selftest "$@"
