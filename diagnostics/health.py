"""
diagnostics/health.py — Component health tracking.

Each subsystem registers a health slot; the pipeline updates slots each
cycle.  A slot that stops receiving OK updates for longer than
``health_degrade_after_s`` seconds is marked DEGRADED.  Faults are
explicit (camera failure, sensor timeout, …) and surface as reason codes
in the safety decision.
"""

from __future__ import annotations

import time
from typing import Optional

from core.models import ComponentHealth, HealthStatus

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAULT = "FAULT"
STATUS_UNKNOWN = "UNKNOWN"


class HealthMonitor:
    def __init__(self, degrade_after_s: float = 3.0) -> None:
        self._degrade_after = float(degrade_after_s)
        self._slots: dict[str, dict] = {}

    def register(self, name: str) -> None:
        self._slots.setdefault(name, {
            "status": STATUS_UNKNOWN,
            "detail": "",
            "last_ok": 0.0,
            "last_update": 0.0,
        })

    def mark_ok(self, name: str, detail: str = "") -> None:
        slot = self._slots.setdefault(name, {})
        now = time.time()
        slot.update(status=STATUS_OK, detail=detail, last_ok=now, last_update=now)

    def mark_fault(self, name: str, detail: str = "") -> None:
        slot = self._slots.setdefault(name, {})
        slot.update(status=STATUS_FAULT, detail=detail, last_update=time.time())

    def mark_degraded(self, name: str, detail: str = "") -> None:
        slot = self._slots.setdefault(name, {})
        slot.update(status=STATUS_DEGRADED, detail=detail, last_update=time.time())

    def status_of(self, name: str) -> str:
        return self._slots.get(name, {}).get("status", STATUS_UNKNOWN)

    def health(self) -> HealthStatus:
        now = time.time()
        components: dict[str, str] = {}
        for name, slot in self._slots.items():
            status = slot.get("status", STATUS_UNKNOWN)
            if status == STATUS_OK and now - slot.get("last_ok", 0.0) > self._degrade_after:
                status = STATUS_DEGRADED
            components[name] = status

        overall = STATUS_OK
        for status in components.values():
            if status == STATUS_FAULT:
                overall = STATUS_FAULT
                break
            if status == STATUS_DEGRADED and overall == STATUS_OK:
                overall = STATUS_DEGRADED
        if not components:
            overall = STATUS_UNKNOWN

        return HealthStatus(
            components=components,
            overall=overall,
            timestamp=now,
        )

    def reset(self) -> None:
        self._slots.clear()