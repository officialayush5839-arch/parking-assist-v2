"""
alerts/mock_alerts.py — Mock alert hardware (console).

Used in simulation / camera mode on a development PC.  Everything here is
clearly a MOCK — no GPIO is touched.
"""

from __future__ import annotations

from alerts.buzzer_controller import MockBuzzer
from alerts.led_controller import MockLEDBank

__all__ = ["MockBuzzer", "MockLEDBank"]