"""
datalog/base.py — Rotating JSON-Lines file writer.

Appends one JSON object per line; rotates the file when it exceeds
``rotate_bytes`` (keeps ``rotate_backups`` old files).  Writes are
synchronous and buffered by the OS; the safety loop never waits on
log I/O because logging is invoked on a throttled cadence.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from core.models import to_jsonable


class RotatingJSONLWriter:
    def __init__(self, directory: str | Path, name: str,
                 rotate_bytes: int = 10_485_760,
                 rotate_backups: int = 3) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._name = name
        self._rotate_bytes = int(rotate_bytes)
        self._backups = max(0, int(rotate_backups))
        self._lock = threading.Lock()
        self._fh = None
        self._size = 0
        self._open()

    def _open(self) -> None:
        path = self._dir / f"{self._name}.jsonl"
        self._fh = open(path, "a", encoding="utf-8")
        self._size = os.path.getsize(path) if path.exists() else 0

    def _rotate(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass
        base = self._dir / f"{self._name}.jsonl"
        for i in range(self._backups, 0, -1):
            src = self._dir / f"{self._name}.{i - 1}.jsonl" if i > 1 else base
            dst = self._dir / f"{self._name}.{i}.jsonl"
            if src.exists():
                dst.write_bytes(src.read_bytes())
                src.unlink()
        self._open()

    def write(self, record: dict[str, Any]) -> None:
        if self._fh is None:
            return
        line = json.dumps(to_jsonable(record), default=str)
        with self._lock:
            self._fh.write(line + "\n")
            self._size += len(line) + 1
            if self._size >= self._rotate_bytes:
                self._rotate()

    def close(self) -> None:
        with self._lock:
            if self._fh is not None:
                try:
                    self._fh.close()
                except Exception:
                    pass
                self._fh = None