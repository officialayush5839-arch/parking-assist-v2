"""
core/errors.py — Meaningful exception classes for the parking-assist system.

Every subsystem raises a typed exception so the runtime can degrade
gracefully instead of crashing.  "Unavailable" exceptions signal that a
component (detector backend, hardware driver, model) is missing and a
MOCK / SIMULATION fallback should be used.
"""


class ParkingAssistError(Exception):
    """Base class for all project-specific errors."""


class ConfigError(ParkingAssistError):
    """Configuration file is missing, malformed, or fails validation."""


class HardwareError(ParkingAssistError):
    """A physical hardware component failed or cannot be opened."""


class CameraError(HardwareError):
    """Camera open/read/close failure."""


class SensorError(HardwareError):
    """Distance-sensor failure."""


class SensorTimeout(SensorError):
    """A sensor read timed out."""


class CalibrationMissing(ParkingAssistError):
    """Camera calibration is required but not available."""


class ComponentUnavailable(ParkingAssistError):
    """A component (backend, library, or model) is not available.

    The caller should fall back to a MOCK / SIMULATION implementation and
    clearly flag the result as such.
    """


class DetectorUnavailable(ComponentUnavailable):
    """Object-detection backend/model is unavailable."""


class ModelUnavailable(ComponentUnavailable):
    """A trained model file is missing."""


class TrackerUnavailable(ComponentUnavailable):
    """The requested tracking backend is unavailable."""


class PredictorUnavailable(ComponentUnavailable):
    """The requested risk-predictor backend is unavailable."""