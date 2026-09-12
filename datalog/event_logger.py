"""
datalog/event_logger.py — System-event logging (JSONL).

Subscribes to the EventBus and writes every event; events are also echoed
to the Python logger at their severity.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from core.events import EventBus, Severity, SystemEvent
from datalog.base import RotatingJSONLWriter

log = logging.getLogger("kpa.events")

_SEVERITY_TO_LOGGING = {
    Severity.DEBUG: logging.DEBUG,
    Severity.INFO: logging.INFO,
    Severity.WARNING: logging.WARNING,
    Severity.ERROR: logging.ERROR,
    Severity.CRITICAL: logging.CRITICAL,
}


class EventLogger:
    def __init__(self, directory: str | Path, bus: EventBus,
                 rotate_bytes: int = 10_485_760,
                 rotate_backups: int = 3) -> None:
        self._writer = RotatingJSONLWriter(directory, "events",
                                           rotate_bytes, rotate_backups)
        self._unsubscribe = bus.subscribe(self._on_event)

    def _on_event(self, event: SystemEvent) -> None:
        self._writer.write({
            "type": "event",
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "event_type": event.event_type.value,
            "severity": event.severity.value,
            "source": event.source,
            "payload": event.payload,
        })
        log.log(_SEVERITY_TO_LOGGING.get(event.severity, logging.INFO),
                "[%s] %s: %s", event.source, event.event_type.value, event.payload)

    def close(self) -> None:
        self._writer.close()