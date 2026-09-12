"""
datalog/experiment_logger.py — Experiment telemetry logging (JSONL).

One row per cycle with the full feature set needed to train/evaluate the
advisory risk model and the anomaly detector.  Rows are tagged
``source: "simulation" | "camera" | "hardware"`` so synthetic data is
never mistaken for real data.
"""

from __future__ import annotations

from pathlib import Path

from core.models import Telemetry, to_jsonable
from datalog.base import RotatingJSONLWriter


class ExperimentLogger:
    def __init__(self, directory: str | Path, source: str = "simulation",
                 rotate_bytes: int = 10_485_760,
                 rotate_backups: int = 3) -> None:
        self._source = source
        self._writer = RotatingJSONLWriter(directory, "experiment",
                                           rotate_bytes, rotate_backups)

    def log_cycle(self, telemetry: Telemetry,
                  extra: dict | None = None) -> None:
        self._writer.write({
            "type": "experiment",
            "source": self._source,   # simulation | camera | hardware
            "cycle_id": telemetry.cycle_id,
            "timestamp": telemetry.timestamp,
            "state": telemetry.state.value,
            "distance_m": telemetry.distance_m,
            "closing_speed_mps": telemetry.closing_speed_mps,
            "ttc_seconds": telemetry.ttc_seconds,
            "risk_score": telemetry.risk_score,
            "confidence": telemetry.confidence,
            "object_class": telemetry.object_class,
            "fps": telemetry.fps,
            "latency_ms": telemetry.latency_ms,
            "reason_codes": telemetry.reason_codes,
            **(extra or {}),
        })

    def close(self) -> None:
        self._writer.close()