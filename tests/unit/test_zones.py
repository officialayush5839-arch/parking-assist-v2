"""Zone thresholds and distance → zone classification."""

import pytest

from core.models import Zone
from zone.thresholds import ZoneThresholds


def test_classify_boundaries():
    t = ZoneThresholds(safe_min_m=2.5, caution_min_m=1.8,
                       warning_min_m=1.0, critical_min_m=0.5)
    assert t.classify(3.0) == Zone.SAFE
    assert t.classify(2.5) == Zone.SAFE
    assert t.classify(2.0) == Zone.SAFE     # >= caution_min_m (1.8)
    assert t.classify(1.7) == Zone.CAUTION  # < caution_min_m (1.8)
    assert t.classify(1.8) == Zone.SAFE     # exactly at boundary, not <
    assert t.classify(1.2) == Zone.CAUTION  # < caution_min_m (1.8), >= warning_min_m (1.0)
    assert t.classify(0.9) == Zone.WARNING  # < warning_min_m (1.0), >= critical_min_m (0.5)
    assert t.classify(1.0) == Zone.CAUTION  # not < warning_min (1.0), but < caution_min (1.8)
    assert t.classify(0.6) == Zone.WARNING  # not < critical_min (0.5), but < warning_min (1.0)
    assert t.classify(0.5) == Zone.WARNING  # not < critical_min (0.5), but < warning_min (1.0)
    assert t.classify(0.3) == Zone.CRITICAL


def test_invalid_ordering_raises():
    with pytest.raises(ValueError):
        ZoneThresholds(safe_min_m=1.0, caution_min_m=2.0,
                       warning_min_m=0.5, critical_min_m=0.1)


def test_from_cfg(cfg):
    t = ZoneThresholds.from_cfg(cfg)
    assert t.safe_min_m == 2.5
    assert t.critical_min_m == 0.5


def test_zone_severity_ordering():
    assert Zone.FAULT.severity > Zone.CRITICAL.severity > Zone.WARNING.severity
    assert Zone.WARNING.severity > Zone.CAUTION.severity > Zone.SAFE.severity
    assert Zone.SAFE.severity > Zone.UNKNOWN.severity


def test_worst():
    assert Zone.worst([Zone.SAFE, Zone.CRITICAL]) == Zone.CRITICAL
    assert Zone.worst([Zone.FAULT, Zone.CRITICAL]) == Zone.FAULT