"""
display/lcd.py — LCD display abstraction (20x4).

Real backend (I2C HD44780 via RPLCD) imports lazily; the console mock
implements the same interface so the HMI runs anywhere.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from core.errors import ComponentUnavailable


class LCDInterface(ABC):
    """20x4 character display."""

    ROWS = 4
    COLS = 20

    @abstractmethod
    def write(self, lines: list[str]) -> None:
        """Write up to 4 lines of ≤20 chars; pads/truncates as needed."""

    @abstractmethod
    def clear(self) -> None:
        ...

    @abstractmethod
    def backlight(self, on: bool) -> None:
        ...


def _pad_lines(lines: list[str], rows: int, cols: int) -> list[str]:
    out: list[str] = []
    for i in range(rows):
        text = lines[i] if i < len(lines) else ""
        text = text[:cols]
        out.append(text.ljust(cols))
    return out


class MockLCD(LCDInterface):
    """Console LCD; prints each page once per write (rate-limited)."""

    def __init__(self, min_interval_s: float = 0.5) -> None:
        self._interval = min_interval_s
        self._last: dict[str, float] = {}
        self._last_page: Optional[tuple] = None

    def write(self, lines: list[str]) -> None:
        import time  # noqa: PLC0415

        now = time.monotonic()
        if now - self._last.get("write", 0.0) < self._interval:
            return
        self._last["write"] = now
        self._last_page = tuple(_pad_lines(lines, self.ROWS, self.COLS))
        print("\n".join("|" + line + "|" for line in self._last_page))

    def clear(self) -> None:
        self._last_page = None

    def backlight(self, on: bool) -> None:
        pass


class I2CLCD(LCDInterface):
    """I2C HD44780 20x4 LCD (e.g. 0x27 / 0x3F). Requires smbus2 + RPLCD."""

    def __init__(self, address: int = 0x27, cols: int = 20, rows: int = 4) -> None:
        try:
            from RPLCD.i2c import CharLCD  # type: ignore
        except ImportError as exc:
            raise ComponentUnavailable(
                "RPLCD is not installed — cannot initialise the I2C LCD. "
                "Use the mock display on a development PC."
            ) from exc
        self._lcd = CharLCD(i2c_expander="PCF8574", address=address,
                            port=1, cols=cols, rows=rows)
        self._cols = cols
        self._rows = rows

    def write(self, lines: list[str]) -> None:
        self._lcd.clear()
        for i, line in enumerate(_pad_lines(lines, self._rows, self._cols)):
            self._lcd.cursor_pos = (i, 0)
            self._lcd.write_string(line)

    def clear(self) -> None:
        self._lcd.clear()

    def backlight(self, on: bool) -> None:
        self._lcd.backlight_enabled = on