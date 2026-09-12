"""
app/config.py — Application configuration entry point.

Re-exports the loader from ``core.config`` so callers can use either
``from app.config import load_config`` or ``from core.config import ...``.
"""

from __future__ import annotations

from core.config import (
    DEFAULTS,
    PROJECT_ROOT,
    ConfigError,
    Settings,
    load_config,
)

__all__ = ["DEFAULTS", "PROJECT_ROOT", "ConfigError", "Settings", "load_config"]