"""Configuration loading, merging, and validation."""

import pytest

from core.config import load_config
from core.errors import ConfigError


def test_defaults_present():
    cfg = load_config()
    assert cfg.get("system.mode") == "simulation"
    assert cfg.get("safety.zones.critical_min_m") == 0.5
    assert cfg.get("vision.backend") == "auto"
    assert cfg.get("fusion.disagreement_threshold_m") == 0.75


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("KPA_MODE", "camera")
    monkeypatch.setenv("KPA_LOOP_HZ", "30")
    cfg = load_config()
    assert cfg.get("system.mode") == "camera"
    assert cfg.get("system.loop_hz") == 30


def test_programmatic_overrides():
    cfg = load_config(overrides={"safety": {"zones": {"critical_min_m": 0.8}}})
    assert cfg.get("safety.zones.critical_min_m") == 0.8


def test_invalid_zone_order_raises():
    with pytest.raises(ConfigError):
        load_config(overrides={"safety": {"zones": {"safe_min_m": 1.0,
                                                     "caution_min_m": 2.0,
                                                     "warning_min_m": 0.5,
                                                     "critical_min_m": 0.1}}})


def test_invalid_mode_raises():
    with pytest.raises(ConfigError):
        load_config(overrides={"system": {"mode": "nonsense"}})


def test_settings_attribute_access():
    cfg = load_config()
    assert cfg.safety.zones.critical_min_m == 0.5


def test_settings_missing_returns_default():
    cfg = load_config()
    assert cfg.get("does.not.exist", 42) == 42