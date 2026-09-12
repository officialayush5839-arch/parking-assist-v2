"""
datalog/__init__.py — Structured data logging.

⚠ Package is named ``datalog`` (not ``logging``) deliberately: a project
package named ``logging`` would shadow the Python standard library module
when running ``python -m app.main`` from the project root.
"""

from __future__ import annotations

from datalog.base import RotatingJSONLWriter
from datalog.event_logger import EventLogger
from datalog.sensor_logger import SensorLogger
from datalog.vision_logger import VisionLogger
from datalog.experiment_logger import ExperimentLogger

__all__ = [
    "RotatingJSONLWriter",
    "EventLogger",
    "SensorLogger",
    "VisionLogger",
    "ExperimentLogger",
]