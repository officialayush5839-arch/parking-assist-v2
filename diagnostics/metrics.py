"""
diagnostics/metrics.py — Per-stage timing and throughput metrics.

Records stage latencies each cycle and exposes FPS, average/P95 latency,
and dropped-frame counts.  Measurements are real — the benchmark tool and
dashboard read from here.  No FPS values are ever claimed from memory.
"""

from __future__ import annotations

import collections
import time
from typing import Optional


class MetricsCollector:
    def __init__(self, keep_cycles: int = 600) -> None:
        self._keep = max(10, keep_cycles)
        self._cycle_times: collections.deque[float] = collections.deque(maxlen=self._keep)
        self._stage_times: dict[str, collections.deque] = {}
        self._frames = 0
        self._dropped_frames = 0
        self._start = time.monotonic()
        self._stamps: collections.deque[float] = collections.deque(maxlen=100_000)
        self._fps_window_s = 5.0
        self._current: Optional[float] = None

    # ── Stage timing ──────────────────────────────────────────────────────────

    def stage_begin(self, name: str) -> None:
        self._current = time.perf_counter()
        self._stage = name

    def stage_end(self) -> None:
        if self._current is None:
            return
        elapsed = time.perf_counter() - self._current
        dq = self._stage_times.setdefault(self._stage, collections.deque(maxlen=self._keep))
        dq.append(elapsed * 1000.0)  # ms
        self._current = None

    def cycle_end(self, cycle_ms: Optional[float] = None) -> None:
        self._frames += 1
        if cycle_ms is not None:
            self._cycle_times.append(cycle_ms)
        self._stamps.append(time.monotonic())

    def drop_frame(self) -> None:
        self._dropped_frames += 1

    # ── Aggregates ────────────────────────────────────────────────────────────

    def fps(self) -> float:
        """Windowed FPS: cycles completed in the last 5 seconds.  Startup
        time and long stalls do not distort the measurement."""
        now = time.monotonic()
        cutoff = now - self._fps_window_s
        while self._stamps and self._stamps[0] < cutoff:
            self._stamps.popleft()
        return len(self._stamps) / self._fps_window_s

    def average_cycle_ms(self) -> float:
        if not self._cycle_times:
            return 0.0
        return sum(self._cycle_times) / len(self._cycle_times)

    def p95_cycle_ms(self) -> float:
        if not self._cycle_times:
            return 0.0
        values = sorted(self._cycle_times)
        idx = min(len(values) - 1, int(len(values) * 0.95))
        return values[idx]

    def stage_summary_ms(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for name, dq in self._stage_times.items():
            if dq:
                out[name] = round(sum(dq) / len(dq), 3)
        return out

    def snapshot(self) -> dict:
        return {
            "fps": round(self.fps(), 2),
            "avg_cycle_ms": round(self.average_cycle_ms(), 3),
            "p95_cycle_ms": round(self.p95_cycle_ms(), 3),
            "stage_avg_ms": self.stage_summary_ms(),
            "frames": self._frames,
            "dropped_frames": self._dropped_frames,
            "uptime_s": round(time.monotonic() - self._start, 2),
        }

    def reset(self) -> None:
        self._cycle_times.clear()
        self._stage_times.clear()
        self._stamps.clear()
        self._frames = 0
        self._dropped_frames = 0
        self._start = time.monotonic()