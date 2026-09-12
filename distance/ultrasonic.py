"""
distance/ultrasonic.py — Physical distance sensing.

Implements the sensor interface with three backends:

* RealUltrasonicSensor   — GPIO trigger/echo (JSN-SR04T); lazy import of
  the GPIO library, so importing this module works on any OS.  Initialising
  the real backend on a machine without the hardware raises
  ComponentUnavailable.
* MockUltrasonicSensor   — scripted provider (scenario-driven), with noise
  and occasional invalid readings for realism.
* RecordedUltrasonicSensor — replays distance readings from a JSONL log.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional

from core.errors import ComponentUnavailable
from core.models import SensorReading
from distance.distance_validator import validate_ultrasonic
from processing.filters import MedianFilter
from processing.outliers import SpikeRejector

# Provider: (now_wall) -> (distance_m | None, valid)
DistanceProvider = Callable[[float], tuple[Optional[float], bool]]


class DistanceSensorInterface(ABC):
    """Interface for all distance-sensor backends."""

    name: str = "distance_sensor"

    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def read(self) -> SensorReading:
        """Return one validated reading (never raises for a bad read)."""

    @property
    @abstractmethod
    def healthy(self) -> bool:
        ...


@dataclass
class SensorConfig:
    min_range_m: float = 0.05
    max_range_m: float = 4.5
    timeout_s: float = 0.5
    median_window: int = 5
    max_delta_m: float = 2.0          # spike rejection on consecutive reads
    max_age_s: float = 2.0


class RealUltrasonicSensor(DistanceSensorInterface):
    """GPIO trigger/echo ultrasonic (e.g. JSN-SR04T via a logic-level
    converter).  GPIO library is imported lazily; constructing this class
    without hardware support raises ComponentUnavailable."""

    name = "ultrasonic"

    def __init__(self, trigger_pin: int = 17, echo_pin: int = 27,
                 config: Optional[SensorConfig] = None) -> None:
        self._trigger = trigger_pin
        self._echo = echo_pin
        self._cfg = config or SensorConfig()
        try:
            import RPi.GPIO as GPIO  # type: ignore  # noqa: N814
        except ImportError:
            try:
                from tinker_board_sdk import gpio as GPIO  # type: ignore
            except ImportError as exc:
                raise ComponentUnavailable(
                    "No GPIO library (RPi.GPIO / Tinker Board SDK) — "
                    "cannot initialise the real ultrasonic sensor"
                ) from exc
        self._gpio = GPIO
        self._seq = 0
        self._running = False

    def start(self) -> None:
        self._gpio.setmode(self._gpio.BCM)
        self._gpio.setup(self._trigger, self._gpio.OUT)
        self._gpio.setup(self._echo, self._gpio.IN)
        self._running = True

    def stop(self) -> None:
        self._running = False
        try:
            self._gpio.cleanup()
        except Exception:
            pass

    @property
    def healthy(self) -> bool:
        return self._running

    def read(self) -> SensorReading:
        self._seq += 1
        if not self._running:
            return SensorReading(self.name, None, False, time.time(),
                                 self._seq, "NOT_RUNNING")
        try:
            # Trigger
            self._gpio.output(self._trigger, True)
            time.sleep(0.00001)
            self._gpio.output(self._trigger, False)

            # Wait for echo start (timeout)
            start = time.time()
            while self._gpio.input(self._echo) == 0:
                if time.time() - start > self._cfg.timeout_s:
                    return SensorReading(self.name, None, False, time.time(),
                                         self._seq, "TIMEOUT")
            echo_start = time.time()
            while self._gpio.input(self._echo) == 1:
                if time.time() - start > self._cfg.timeout_s * 4:
                    return SensorReading(self.name, None, False, time.time(),
                                         self._seq, "TIMEOUT")
            echo_end = time.time()

            duration = echo_end - echo_start
            distance_m = duration * 343.0 / 2.0  # speed of sound ≈ 343 m/s
            valid, reason = validate_ultrasonic(
                distance_m, self._cfg.min_range_m, self._cfg.max_range_m)
            return SensorReading(self.name, distance_m, valid, time.time(),
                                 self._seq, reason)
        except Exception:
            return SensorReading(self.name, None, False, time.time(),
                                 self._seq, "SENSOR_ERROR")


class MockUltrasonicSensor(DistanceSensorInterface):
    """Scenario/provider-driven mock sensor with noise + occasional faults."""

    name = "mock_ultrasonic"

    def __init__(self, provider: Optional[DistanceProvider] = None,
                 config: Optional[SensorConfig] = None,
                 noise_m: float = 0.03,
                 fault_probability: float = 0.0) -> None:
        self._provider = provider or (lambda now: (None, False))
        self._cfg = config or SensorConfig()
        self._noise_m = noise_m
        self._fault_prob = fault_probability
        self._median = MedianFilter(self._cfg.median_window)
        self._spike = SpikeRejector(self._cfg.max_delta_m)
        self._seq = 0
        self._running = False
        self._faults = 0

    def set_provider(self, provider: DistanceProvider) -> None:
        self._provider = provider

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    @property
    def healthy(self) -> bool:
        return self._running

    @property
    def faults(self) -> int:
        return self._faults

    def read(self) -> SensorReading:
        self._seq += 1
        if not self._running:
            return SensorReading(self.name, None, False, time.time(),
                                 self._seq, "NOT_RUNNING")

        distance_m, valid = self._provider(time.time())

        # Occasional hard fault (sensor outage / timeout)
        if self._fault_prob > 0 and _rng() < self._fault_prob:
            self._faults += 1
            return SensorReading(self.name, None, False, time.time(),
                                 self._seq, "TIMEOUT")

        if not valid or distance_m is None:
            return SensorReading(self.name, None, False, time.time(),
                                 self._seq, "INVALID")

        noisy = distance_m + (2 * _rng() - 1) * self._noise_m
        smoothed = self._median.update(noisy)
        spike = self._spike.update(smoothed)
        value = spike.value if spike.value is not None else smoothed

        ok, reason = validate_ultrasonic(
            value, self._cfg.min_range_m, self._cfg.max_range_m)
        return SensorReading(self.name, value, ok, time.time(),
                             self._seq, reason)


class RecordedUltrasonicSensor(DistanceSensorInterface):
    """Replays distance readings from a JSONL file (see tools/replay_log.py)."""

    name = "recorded_ultrasonic"

    def __init__(self, path: str) -> None:
        import json  # noqa: PLC0415

        self._readings: list[SensorReading] = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if record.get("type") == "sensor":
                    self._readings.append(SensorReading(
                        source="recorded_ultrasonic",
                        distance_m=record.get("distance_m"),
                        valid=bool(record.get("valid", False)),
                        timestamp=float(record.get("timestamp", 0.0)),
                        sequence=int(record.get("sequence", 0)),
                        reason=record.get("reason"),
                    ))
        self._idx = 0
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    @property
    def healthy(self) -> bool:
        return self._running

    def read(self) -> SensorReading:
        if self._idx >= len(self._readings):
            # End of replay: hold the last reading invalid.
            return SensorReading(self.name, None, False, time.time(),
                                 self._seq if hasattr(self, "_seq") else 0, "END_OF_REPLAY")
        reading = self._readings[self._idx]
        self._idx += 1
        return reading


def _rng() -> float:
    # Deterministic-ish uniform noise source (fine for simulation).
    import random  # noqa: PLC0415

    return random.random()