"""
core/models.py — Central typed data models.

All pipeline stages exchange typed structures (dataclasses), never ad-hoc
dicts.  JSON serialization happens only at logging / API boundaries via
:func:`to_jsonable`.
"""

from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


# ─── Enums ────────────────────────────────────────────────────────────────────

class Zone(str, Enum):
    """Deterministic safety zones, ordered by severity (highest first)."""

    FAULT = "FAULT"
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    CAUTION = "CAUTION"
    SAFE = "SAFE"
    UNKNOWN = "UNKNOWN"

    @property
    def severity(self) -> int:
        """Higher = more severe. FAULT is the most severe, UNKNOWN the least."""
        return {
            Zone.FAULT: 5,
            Zone.CRITICAL: 4,
            Zone.WARNING: 3,
            Zone.CAUTION: 2,
            Zone.SAFE: 1,
            Zone.UNKNOWN: 0,
        }[self]

    @classmethod
    def worst(cls, zones: "list[Zone]") -> "Zone":
        """Return the most severe zone in *zones* (FAULT beats CRITICAL, …)."""
        if not zones:
            return Zone.UNKNOWN
        return max(zones, key=lambda z: z.severity)


class TrackState(str, Enum):
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    TEMPORARILY_LOST = "TEMPORARILY_LOST"
    LOST = "LOST"
    REMOVED = "REMOVED"


class Severity(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class RiskClass(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ─── Data models ──────────────────────────────────────────────────────────────

@dataclass
class Detection:
    """One object detection from the vision pipeline."""

    class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2) pixels
    timestamp: float
    frame_id: int
    source: str = "vision"

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def width_px(self) -> int:
        return max(0, self.bbox[2] - self.bbox[0])

    @property
    def height_px(self) -> int:
        return max(0, self.bbox[3] - self.bbox[1])


@dataclass
class TrackedObject:
    """A persistent object identity maintained by the tracker."""

    track_id: int
    class_name: str
    bbox: tuple[int, int, int, int]
    center_x: float
    center_y: float
    estimated_distance: Optional[float]
    velocity: float = 0.0          # closing speed, m/s (positive = approaching)
    confidence: float = 0.0
    first_seen: float = 0.0
    last_seen: float = 0.0
    state: TrackState = TrackState.NEW


@dataclass
class SensorReading:
    """A single physical distance-sensor reading."""

    source: str                 # "ultrasonic" | "mock_ultrasonic" | ...
    distance_m: Optional[float]
    valid: bool
    timestamp: float
    sequence: int = 0
    reason: Optional[str] = None  # e.g. "TIMEOUT", "OUT_OF_RANGE", "INVALID"


@dataclass
class DistanceEstimate:
    """A vision-based (monocular) distance estimate."""

    distance_m: Optional[float]
    confidence: float
    method: str                 # "monocular_geometry" | ...
    valid: bool
    timestamp: float
    reason: Optional[str] = None


@dataclass
class FusionResult:
    """Output of the sensor/vision fusion stage."""

    fused_distance_m: Optional[float]
    confidence: float
    method: str                 # "weighted" | "ultrasonic_only" | "monocular_only" | "none"
    valid: bool
    timestamp: float
    vision_distance: Optional[float] = None
    sensor_distance: Optional[float] = None
    agreement: Optional[float] = None      # 0..1, 1 = perfect agreement
    disagreement: bool = False
    sensor_valid: bool = False
    vision_valid: bool = False
    reason_codes: list[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    """Advisory ML/deterministic risk output. NEVER gates safety directly."""

    risk_score: float           # 0..1
    risk_class: RiskClass
    confidence: float
    method: str                 # "deterministic_ttc" | "ml" | "mock"
    timestamp: float
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class SafetyDecision:
    """Final deterministic safety decision."""

    state: Zone
    distance_m: Optional[float]
    closing_speed_mps: Optional[float]
    ttc_seconds: Optional[float]     # None / inf ⇒ no collision path
    risk_score: Optional[float]
    confidence: float
    reason_codes: list[str]
    timestamp: float
    sources: list[str] = field(default_factory=list)  # e.g. ["ultrasonic", "vision"]

    @property
    def jsonable(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass
class ComponentHealth:
    """Health of one subsystem (camera, sensor, detector, …)."""

    name: str
    status: str                 # OK | DEGRADED | FAULT | UNKNOWN
    detail: str = ""
    timestamp: float = 0.0


@dataclass
class HealthStatus:
    """Aggregated system health."""

    components: dict[str, str] = field(default_factory=dict)
    overall: str = "UNKNOWN"
    timestamp: float = 0.0


@dataclass
class Telemetry:
    """Per-cycle summary published for logging, console, and the dashboard."""

    cycle_id: int
    timestamp: float
    state: Zone
    distance_m: Optional[float]
    confidence: float
    object_class: Optional[str]
    closing_speed_mps: Optional[float]
    ttc_seconds: Optional[float]
    risk_score: Optional[float]
    fps: float
    latency_ms: float
    detections: int
    tracks: int
    reason_codes: list[str] = field(default_factory=list)
    verbose: dict[str, Any] = field(default_factory=dict)


# ─── Serialization helpers ────────────────────────────────────────────────────

def _clean(value: Any) -> Any:
    """Make a value JSON-safe (handle dataclasses, enums, tuples, NaN/inf)."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_clean(v) for v in value]
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, set)):
        return [_clean(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if hasattr(value, "__dataclass_fields__"):
        return to_jsonable(value)
    return value


def to_jsonable(obj: Any) -> Any:
    """Convert a dataclass (or nested structure) into a JSON-safe dict."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _clean(v) for k, v in asdict(obj).items()}
    return _clean(obj)


def now_wall() -> float:
    """Wall-clock Unix timestamp (seconds), used for all logged timestamps."""
    return time.time()