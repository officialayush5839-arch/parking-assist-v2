"""
datalog/sensor_logger.py — Sensor-reading logging (JSONL).

Every validated sensor reading is timestamped and written with source,
sequence, validity, and reason.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.models import SensorReading
from datalog.base import RotatingJSONLWriter


class SensorLogger:
    def __init__(self, directory: str | Path,
                 rotate_bytes: int = 10_485_760,
                 rotate_backups: int = 3) -> None:
        self._writer = RotatingJSONLWriter(directory, "sensor",
                                           rotate_bytes, rotate_backups)

    def log(self, reading: SensorReading) -> None:
        self._writer.write({
            "type": "sensor",
            "timestamp": reading.timestamp,
            "source": reading.source,
            "distance_m": reading.distance_m,
            "valid": reading.valid,
            "sequence": reading.sequence,
            "reason": reading.reason,
        })

    def close(self) -> None:
        self._writer.close()