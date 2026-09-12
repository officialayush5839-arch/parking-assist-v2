"""
display/hmi.py — Human-machine interface controller.

Rotates 3 pages on the 20x4 LCD:

    Page 1: STATE / DIST / OBJ / CONF
    Page 2: SPEED / TTC / RISK
    Page 3: CAM / US / ML / FPS

Page rotation is time-based and throttled so the HMI never blocks the
safety loop.
"""

from __future__ import annotations

from typing import Optional

from core.models import Telemetry
from display.lcd import LCDInterface
from ml.ttc import ttc_display
from processing.filters import RateLimiter


class HMIController:
    def __init__(self, lcd: Optional[LCDInterface],
                 page_interval_s: float = 2.0,
                 min_refresh_s: float = 0.5) -> None:
        self._lcd = lcd
        self._page_interval = page_interval_s
        self._refresh = RateLimiter(min_refresh_s)
        self._page = 0
        self._last_rotate: float = 0.0

    @property
    def available(self) -> bool:
        return self._lcd is not None

    def update(self, telemetry: Telemetry, now: float) -> None:
        if self._lcd is None:
            return
        if now - self._last_rotate >= self._page_interval:
            self._last_rotate = now
            self._page = (self._page + 1) % 3
        if not self._refresh.allow(now):
            return
        self._lcd.write(self._page_lines(telemetry, self._page))

    # ── Internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _page_lines(t: Telemetry, page: int) -> list[str]:
        dist = f"{t.distance_m:.2f}m" if t.distance_m is not None else "?"
        conf = f"{t.confidence * 100:.0f}%" if t.confidence else "-"
        obj = (t.object_class or "-").upper()
        speed = f"{t.closing_speed_mps:.2f}m/s" if t.closing_speed_mps is not None else "-"
        risk = f"{t.risk_score * 100:.0f}%" if t.risk_score is not None else "-"

        if page == 0:
            return [
                f"STATE: {t.state.value}",
                f"DIST : {dist}",
                f"OBJ  : {obj}",
                f"CONF : {conf}",
            ]
        if page == 1:
            return [
                f"SPEED: {speed}",
                f"TTC  : {ttc_display(t.ttc_seconds)}",
                f"RISK : {risk}",
                f"CYCL : #{t.cycle_id}",
            ]
        v = t.verbose
        ml = v.get("ml", "-")
        ml_short = {"deterministic_ttc": "DET", "ml": "ML",
                    "mock": "MOCK"}.get(ml, ml[:4])
        return [
            f"CAM : {v.get('camera', '-')}",
            f"US  : {v.get('sensor', '-')}",
            f"ML  : {ml_short}",
            f"FPS : {t.fps:.1f}",
        ]