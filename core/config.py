"""
core/config.py — Configuration system.

Loads YAML files from ``config/`` (with defaults baked in), merges optional
programmatic overrides and environment variables, and validates the result.
Every threshold / pin / path lives here — never hard-coded in modules.

A small dependency-free YAML-subset parser is used only when PyYAML is not
installed, so the simulation runs on a bare Python install.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

from core.errors import ConfigError

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ─── Defaults (merged under the YAML files) ───────────────────────────────────

DEFAULTS: dict[str, Any] = {
    "system": {
        "mode": "simulation",
        "loop_hz": 15,
        "verbose": False,
        "duration_s": 0,
        "scenario": None,
    },
    "vision": {
        "backend": "auto",
        "model": "yolov8n",
        "model_path": None,
        "confidence_threshold": 0.40,
        "input_width": 640,
        "input_height": 480,
        "denoise": False,
        "classes_of_interest": ["person", "car", "truck", "bus", "motorcycle", "bicycle", "suitcase"],
    },
    "tracking": {
        "backend": "auto",
        "iou_threshold": 0.30,
        "max_lost_frames": 20,
        "velocity": {
            "ema_alpha": 0.4,
            "max_plausible_mps": 5.0,
            "history_s": 3.0,
        },
    },
    "distance": {
        "ultrasonic": {
            "enabled": True,
            "min_range_m": 0.05,
            "max_range_m": 4.5,
            "timeout_s": 0.50,
            "sample_hz": 20,
            "median_window": 5,
        },
        "monocular": {
            "enabled": True,
            "focal_length_px": 600.0,
            "known_widths_m": {
                "person": 0.50, "car": 1.80, "truck": 2.40, "bus": 2.50,
                "motorcycle": 0.80, "bicycle": 0.60, "suitcase": 0.50,
            },
            "max_distance_m": 20.0,
            "min_distance_m": 0.20,
        },
    },
    "fusion": {
        "enabled": True,
        "disagreement_threshold_m": 0.75,
        "conservative_on_disagreement": True,
        "sensor_trust": 0.90,
    },
    "risk": {
        "predictor": "deterministic_ttc",
        "model_path": None,
        "high_closing_speed_mps": 1.0,
        "ttc_warning_s": 3.0,
        "ttc_critical_s": 1.5,
    },
    "anomaly": {
        "enabled": False,
        "contamination": 0.05,
    },
    "alerts": {
        "enabled": True,
        "buzzer_enabled": True,
        "led_mapping": {
            "safe": "green", "caution": "yellow", "warning": "orange",
            "critical": "red", "fault": "blue", "unknown": "off",
        },
    },
    "diagnostics": {
        "sample_every_s": 1.0,
        "health_degrade_after_s": 3.0,
    },
    "dashboard": {
        "enabled": False,
        "host": "127.0.0.1",
        "port": 8765,
    },
    "acquisition": {
        "queue_size": 32,
        "drop_frames_when_busy": True,
    },
    "camera": {
        "backend": "auto",
        "width": 640,
        "height": 480,
        "fps": 15,
        "source": 0,
        "video_file": None,
        "calibration_file": "config/camera_calibration.yaml",
        "reconnect_attempts": 3,
        "reconnect_delay_s": 0.5,
        "low_light_threshold": 40,
    },
    "safety": {
        "zones": {
            "safe_min_m": 2.5,
            "caution_min_m": 1.8,
            "warning_min_m": 1.0,
            "critical_min_m": 0.5,
        },
        "stability_frames": 3,
        "hard_safety_enabled": True,
        "high_closing_speed_mps": 1.0,
        "ttc_warning_s": 3.0,
        "ttc_critical_s": 1.5,
        "no_distance_state": "FAULT",
        "degraded_confidence": 0.40,
    },
    "logging": {
        "directory": "logs",
        "level": "INFO",
        "jsonl": True,
        "rotate_bytes": 10_485_760,
        "rotate_backups": 3,
        "console_telemetry": True,
        "verbose_telemetry": False,
    },
}

_ENV_OVERRIDES: dict[str, tuple[str, Any]] = {
    "KPA_MODE": ("system.mode", str),
    "KPA_LOOP_HZ": ("system.loop_hz", int),
    "KPA_VERBOSE": ("system.verbose", bool),
    "KPA_DURATION": ("system.duration_s", float),
    "KPA_SCENARIO": ("system.scenario", str),
    "KPA_LOG_LEVEL": ("logging.level", str),
    "KPA_LOG_DIR": ("logging.directory", str),
    "KPA_DASHBOARD": ("dashboard.enabled", bool),
    "KPA_DASHBOARD_PORT": ("dashboard.port", int),
}


# ─── Mini YAML-subset parser (fallback when PyYAML is missing) ────────────────

def _scalar(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    low = raw.lower()
    if low in ("null", "~", "none"):
        return None
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _parse_block(entries: list[tuple[int, str]], idx: int, indent: int) -> tuple[Any, int]:
    node: dict[str, Any] = {}
    i = idx
    while i < len(entries):
        ind, raw = entries[i]
        if ind < indent:
            break
        if ind > indent:
            raise ValueError(f"mini-yaml: unexpected indentation at {raw!r}")
        if raw.startswith("- "):
            items, i = _parse_list(entries, i, indent)
            return items, i
        if ": " in raw:
            key, _, val = raw.partition(": ")
            node[key.strip()] = _scalar(val)
            i += 1
        elif raw.endswith(":"):
            key = raw[:-1].strip()
            if i + 1 < len(entries) and entries[i + 1][0] > indent:
                child, i = _parse_block(entries, i + 1, entries[i + 1][0])
                node[key] = child
            else:
                node[key] = None
                i += 1
        else:
            raise ValueError(f"mini-yaml: cannot parse line {raw!r}")
    return node, i


def _parse_list(entries: list[tuple[int, str]], idx: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    i = idx
    while i < len(entries):
        ind, raw = entries[i]
        if ind != indent or not raw.startswith("- "):
            break
        items.append(_scalar(raw[2:].strip()))
        i += 1
    return items, i


def _parse_mini_yaml(text: str) -> dict[str, Any]:
    entries: list[tuple[int, str]] = []
    for line in text.splitlines():
        if " #" in line:
            line = line.split(" #", 1)[0]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        entries.append((indent, stripped))
    if not entries:
        return {}
    value, _ = _parse_block(entries, 0, entries[0][0])
    return value if isinstance(value, dict) else {"value": value}


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML file with PyYAML, falling back to the mini parser."""
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except ImportError:
        return _parse_mini_yaml(text)


# ─── Merge + validation ───────────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _apply_env(cfg: dict, env: dict) -> None:
    for var, (dotted, cast) in _ENV_OVERRIDES.items():
        raw = env.get(var)
        if raw is None or raw == "":
            continue
        try:
            value: Any = cast(raw)
        except ValueError:
            raise ConfigError(f"Invalid value for {var}: {raw!r}") from None
        _set_dotted(cfg, dotted, value)


def _set_dotted(cfg: dict, dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cur = cfg
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def _validate(cfg: dict) -> None:
    mode = cfg.get("system", {}).get("mode")
    if mode not in ("simulation", "camera", "hardware", "demo", "selftest"):
        raise ConfigError(f"Unknown system.mode: {mode!r}")

    zones = cfg.get("safety", {}).get("zones", {})
    names = ("safe_min_m", "caution_min_m", "warning_min_m", "critical_min_m")
    for name in names:
        if name not in zones or not isinstance(zones[name], (int, float)):
            raise ConfigError(f"safety.zones.{name} missing or not numeric")
    if not (zones["safe_min_m"] > zones["caution_min_m"] > zones["warning_min_m"] > zones["critical_min_m"] > 0):
        raise ConfigError(
            "Safety zone thresholds must satisfy "
            "safe > caution > warning > critical > 0 "
            f"(got {zones})"
        )

    predictor = cfg.get("risk", {}).get("predictor")
    if predictor not in ("deterministic_ttc", "ml", "mock"):
        raise ConfigError(f"Unknown risk.predictor: {predictor!r}")

    backend = cfg.get("vision", {}).get("backend")
    if backend not in ("auto", "yolo", "tflite", "mock"):
        raise ConfigError(f"Unknown vision.backend: {backend!r}")


# ─── Public API ───────────────────────────────────────────────────────────────

class Settings:
    """Dict wrapper with dotted-path access: ``cfg.safety.zones.safe_min_m``."""

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, Any]) -> None:
        object.__setattr__(self, "_data", data)

    def __getattr__(self, name: str) -> Any:
        data = object.__getattribute__(self, "_data")
        if name in data:
            value = data[name]
            return Settings(value) if isinstance(value, dict) else value
        raise AttributeError(name)

    def get(self, dotted: str, default: Any = None) -> Any:
        cur: Any = self._data
        for part in dotted.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur

    def as_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Settings({self._data!r})"


def load_config(
    config_dir: str | os.PathLike | None = None,
    overrides: dict[str, Any] | None = None,
    env: dict | None = None,
) -> Settings:
    """Load and validate configuration.

    Merge order (later wins): baked-in defaults → config/*.yaml →
    programmatic *overrides* → environment variables.
    """
    root = Path(config_dir) if config_dir else PROJECT_ROOT
    merged = copy.deepcopy(DEFAULTS)

    for name in ("config.yaml", "safety.yaml", "camera.yaml", "logging.yaml"):
        path = root / "config" / name
        if path.is_file():
            try:
                data = load_yaml_file(path)
            except Exception as exc:
                raise ConfigError(f"Failed to parse {path}: {exc}") from exc
            if data:
                _deep_merge(merged, data)

    if overrides:
        _deep_merge(merged, overrides)
    if env is None:
        env = os.environ
    _apply_env(merged, env)
    _validate(merged)
    return Settings(merged)