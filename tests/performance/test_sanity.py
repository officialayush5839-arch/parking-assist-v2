"""Performance sanity tests.

These are NOT claims about the Tinker Board — they only guard against
gross performance regressions on the development machine (Python 3.14,
Windows). Measured numbers are reported, never fabricated.

Run the real benchmark with:

    python -m tools.benchmark
"""

from __future__ import annotations

import time

from processing.filters import ExponentialMovingAverage
from ml.ttc import compute_ttc
from fusion.confidence_fusion import ConfidenceFusion
from core.models import DistanceEstimate, SensorReading


def _bench(fn, n: int) -> float:
    start = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - start) / n * 1000.0  # ms per call


def test_filter_timing() -> None:
    f = ExponentialMovingAverage(alpha=0.3)
    ms = _bench(lambda: f.update(1.0), 20_000)
    assert ms < 0.1, f"exponential smoother too slow: {ms:.4f} ms/call"


def test_ttc_timing() -> None:
    ms = _bench(lambda: compute_ttc(1.2, 0.5), 20_000)
    assert ms < 0.05, f"ttc too slow: {ms:.4f} ms/call"


def test_fusion_timing() -> None:
    fusion = ConfidenceFusion()

    def one() -> None:
        fusion.fuse(
            SensorReading(source="us", distance_m=1.2, valid=True, timestamp=1.0),
            DistanceEstimate(distance_m=1.4, valid=True, confidence=0.7, method="monocular_geometry", timestamp=1.0),
            now=1.0,
        )

    ms = _bench(one, 20_000)
    assert ms < 0.1, f"fusion too slow: {ms:.4f} ms/call"