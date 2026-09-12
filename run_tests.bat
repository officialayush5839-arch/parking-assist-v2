@echo off
echo KPIT Parking Assist V2.0 - Running Tests
echo =========================================
python -m pytest --import-mode=importlib -q %*
