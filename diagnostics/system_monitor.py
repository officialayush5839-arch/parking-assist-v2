"""
diagnostics/system_monitor.py — Host resource monitoring.

CPU / RAM via psutil (already a core dependency); temperature only where
the platform exposes it.  All measurements are best-effort and never
block the safety loop.
"""

from __future__ import annotations

from typing import Optional


class SystemMonitor:
    def __init__(self) -> None:
        try:
            import psutil  # type: ignore  # noqa: F401

            self._psutil = True
        except ImportError:
            self._psutil = False

    def cpu_percent(self) -> Optional[float]:
        if not self._psutil:
            return None
        import psutil  # noqa: PLC0415

        return round(float(psutil.cpu_percent(interval=None)), 1)

    def ram_mb(self) -> Optional[float]:
        if not self._psutil:
            return None
        import psutil  # noqa: PLC0415

        return round(float(psutil.virtual_memory().used) / (1024 * 1024), 1)

    def temperature_c(self) -> Optional[float]:
        """CPU temperature where available (e.g. /sys/class/thermal on the
        Tinker Board).  Returns None on platforms without a sensor."""
        try:
            for path in (
                "/sys/class/thermal/thermal_zone0/temp",
                "/sys/class/hwmon/hwmon0/temp1_input",
            ):
                with open(path, encoding="utf-8") as fh:
                    raw = float(fh.read().strip())
                return round(raw / 1000.0, 1)
        except (OSError, ValueError):
            return None

    def snapshot(self) -> dict:
        return {
            "cpu_percent": self.cpu_percent(),
            "ram_mb": self.ram_mb(),
            "temperature_c": self.temperature_c(),
        }