"""
acquisition/sensor_reader.py — Distance-sensor acquisition wrapper.

Wraps a DistanceSensorInterface, adds sequence numbering and read
statistics, and keeps the most recent reading available to the pipeline.
"""

from __future__ import annotations

from typing import Optional

from acquisition.timestamp import now_wall
from core.models import SensorReading
from distance.ultrasonic import DistanceSensorInterface


class SensorReader:
    def __init__(self, sensor: DistanceSensorInterface) -> None:
        self._sensor = sensor
        self._last: Optional[SensorReading] = None
        self._reads = 0
        self._invalid = 0

    @property
    def sensor(self) -> DistanceSensorInterface:
        return self._sensor

    @property
    def healthy(self) -> bool:
        return self._sensor.healthy

    @property
    def last(self) -> Optional[SensorReading]:
        return self._last

    @property
    def stats(self) -> dict:
        return {
            "reads": self._reads,
            "invalid": self._invalid,
        }

    def read(self) -> SensorReading:
        reading = self._sensor.read()
        self._reads += 1
        if not reading.valid:
            self._invalid += 1
        self._last = reading
        return reading