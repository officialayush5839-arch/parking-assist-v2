"""
core/events.py — Standardized event system.

Components publish :class:`SystemEvent` objects onto a shared
:class:`EventBus`; loggers, the dashboard, and diagnostics subscribe.
Events are the observability backbone and are never used to gate safety.
"""

from __future__ import annotations

import itertools
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from core.models import Severity


class EventType(str, Enum):
    SYSTEM_STARTED = "SYSTEM_STARTED"
    SYSTEM_STOPPED = "SYSTEM_STOPPED"
    CAMERA_STARTED = "CAMERA_STARTED"
    CAMERA_FAILURE = "CAMERA_FAILURE"
    CAMERA_RECOVERED = "CAMERA_RECOVERED"
    SENSOR_STARTED = "SENSOR_STARTED"
    SENSOR_FAILURE = "SENSOR_FAILURE"
    SENSOR_TIMEOUT = "SENSOR_TIMEOUT"
    SENSOR_RECOVERED = "SENSOR_RECOVERED"
    INVALID_SENSOR_VALUE = "INVALID_SENSOR_VALUE"
    DETECTION_STARTED = "DETECTION_STARTED"
    DETECTOR_FAILURE = "DETECTOR_FAILURE"
    DETECTOR_FALLBACK = "DETECTOR_FALLBACK"      # real backend → mock
    TRACKER_FAILURE = "TRACKER_FAILURE"
    MODEL_LOADED = "MODEL_LOADED"
    MODEL_FAILURE = "MODEL_FAILURE"
    CALIBRATION_MISSING = "CALIBRATION_MISSING"
    SENSOR_DISAGREEMENT = "SENSOR_DISAGREEMENT"
    SAFETY_STATE_CHANGED = "SAFETY_STATE_CHANGED"
    CRITICAL_ALERT = "CRITICAL_ALERT"
    FAULT_DETECTED = "FAULT_DETECTED"
    ALERT_TRIGGERED = "ALERT_TRIGGERED"
    OBJECT_DETECTED = "OBJECT_DETECTED"
    TRACK_CREATED = "TRACK_CREATED"
    TRACK_LOST = "TRACK_LOST"
    SELF_TEST_STARTED = "SELF_TEST_STARTED"
    SELF_TEST_RESULT = "SELF_TEST_RESULT"


@dataclass
class SystemEvent:
    """A single standardized event."""

    event_type: EventType
    severity: Severity
    source: str
    timestamp: float
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "source": self.source,
            "payload": self.payload,
        }


Listener = Callable[[SystemEvent], None]


class EventBus:
    """Thread-safe publish/subscribe event bus with a bounded recent-history."""

    def __init__(self, history_size: int = 500) -> None:
        self._listeners: list[Listener] = []
        self._lock = threading.Lock()
        self._ids = itertools.count(1)
        self._recent: list[SystemEvent] = []
        self._history_size = max(10, history_size)

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        """Register *listener*; returns an unsubscribe callable."""
        with self._lock:
            self._listeners.append(listener)

        def unsubscribe() -> None:
            with self._lock:
                try:
                    self._listeners.remove(listener)
                except ValueError:
                    pass

        return unsubscribe

    def publish(self, event_type: EventType, severity: Severity,
                source: str, payload: dict[str, Any] | None = None) -> SystemEvent:
        """Create and fan out an event. Never raises for listener errors."""
        event = SystemEvent(
            event_id=next(self._ids),
            event_type=event_type,
            severity=severity,
            source=source,
            timestamp=time.time(),
            payload=payload or {},
        )
        with self._lock:
            self._recent.append(event)
            if len(self._recent) > self._history_size:
                del self._recent[: len(self._recent) - self._history_size]
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                # Observability must never break the safety pipeline.
                continue
        return event

    def recent(self, limit: int = 100) -> list[SystemEvent]:
        """Most recent events, newest last."""
        with self._lock:
            return list(self._recent[-limit:])

    def clear(self) -> None:
        with self._lock:
            self._recent.clear()