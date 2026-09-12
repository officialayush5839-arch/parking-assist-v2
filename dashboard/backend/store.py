"""
dashboard/backend/store.py — In-memory telemetry store.

Bounded ring buffers shared by the runtime (writer) and the dashboard
(readers).  Monitoring only — this store never influences safety.
"""

from __future__ import annotations

import collections
import time
from typing import Any, Optional

from core.events import EventBus
from core.models import Telemetry, to_jsonable


class TelemetryStore:
    def __init__(self, capacity: int = 1000) -> None:
        self._capacity = max(10, capacity)
        self._telemetry: collections.deque = collections.deque(maxlen=self._capacity)
        self._events: collections.deque = collections.deque(maxlen=500)
        self._safety: collections.deque = collections.deque(maxlen=self._capacity)
        self._detections: collections.deque = collections.deque(maxlen=200)
        self._tracks: collections.deque = collections.deque(maxlen=200)
        self._health: dict[str, Any] = {}
        self._metrics: dict[str, Any] = {}
        self._config: dict[str, Any] = {}

    def subscribe_events(self, bus: EventBus) -> None:
        bus.subscribe(self._on_event)

    def _on_event(self, event) -> None:
        self._events.append(event.to_dict())

    # ── Writers ───────────────────────────────────────────────────────────────

    def push_telemetry(self, telemetry: Telemetry) -> None:
        data = to_jsonable(telemetry)
        self._telemetry.append(data)
        self._safety.append({
            "state": data["state"],
            "distance_m": data["distance_m"],
            "risk_score": data["risk_score"],
            "ttc_seconds": data["ttc_seconds"],
            "closing_speed_mps": data["closing_speed_mps"],
            "confidence": data["confidence"],
            "timestamp": data["timestamp"],
            "reason_codes": data["reason_codes"],
        })

    def push_detections(self, detections: list[dict]) -> None:
        if detections:
            self._detections.extend(detections)

    def push_tracks(self, tracks: list[dict]) -> None:
        if tracks:
            self._tracks.extend(tracks)

    def push_health(self, health: dict) -> None:
        self._health = health

    def push_metrics(self, metrics: dict) -> None:
        self._metrics = metrics

    def push_config(self, config: dict) -> None:
        self._config = config

    # ── Readers (all return JSON-safe data) ───────────────────────────────────

    def latest_telemetry(self) -> Optional[dict]:
        return self._telemetry[-1] if self._telemetry else None

    def latest_safety(self) -> dict:
        return self._safety[-1] if self._safety else {}

    def recent_events(self, limit: int = 100) -> list[dict]:
        return list(self._events)[-limit:]

    def recent_telemetry(self, limit: int = 200) -> list[dict]:
        return list(self._telemetry)[-limit:]

    def recent_detections(self, limit: int = 50) -> list[dict]:
        return list(self._detections)[-limit:]

    def recent_tracks(self, limit: int = 50) -> list[dict]:
        return list(self._tracks)[-limit:]

    def health(self) -> dict:
        return self._health or {"components": {}, "overall": "UNKNOWN",
                                "timestamp": time.time()}

    def metrics(self) -> dict:
        return self._metrics or {}

    def config(self) -> dict:
        return self._config or {}