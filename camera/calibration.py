"""
camera/calibration.py — Camera calibration support.

Holds intrinsic matrix, distortion coefficients, image dimensions, and a
version tag.  Load/save to YAML (via PyYAML or the mini parser).  When no
calibration file exists the system runs in an uncalibrated mode and
monocular distance is flagged CALIBRATION_NOT_AVAILABLE.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from core.config import load_yaml_file
from core.errors import CalibrationMissing

CALIBRATION_VERSION = "1.0"


@dataclass
class CameraCalibration:
    camera_matrix: list[list[float]] = field(default_factory=lambda: _identity3())
    dist_coeffs: list[float] = field(default_factory=list)
    image_width: int = 640
    image_height: int = 480
    version: str = CALIBRATION_VERSION

    @classmethod
    def from_file(cls, path: str | Path) -> "CameraCalibration":
        p = Path(path)
        if not p.is_file():
            raise CalibrationMissing(f"Calibration file not found: {p}")
        try:
            data = load_yaml_file(p)
        except Exception as exc:
            raise CalibrationMissing(f"Cannot parse calibration file {p}: {exc}") from exc
        return cls(
            camera_matrix=data.get("camera_matrix") or _identity3(),
            dist_coeffs=data.get("dist_coeffs") or [],
            image_width=int(data.get("image_width", 640)),
            image_height=int(data.get("image_height", 480)),
            version=str(data.get("version", CALIBRATION_VERSION)),
        )

    @classmethod
    def load_or_none(cls, path: str | Path | None) -> Optional["CameraCalibration"]:
        if not path:
            return None
        try:
            return cls.from_file(path)
        except CalibrationMissing:
            return None

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_yaml_dump(asdict(self)), encoding="utf-8")

    @property
    def available(self) -> bool:
        return bool(self.camera_matrix) and self.camera_matrix[0][0] > 0

    def focal_length_px(self) -> Optional[float]:
        """fx from the intrinsic matrix, when available."""
        if not self.available:
            return None
        return float(self.camera_matrix[0][0])


def _identity3() -> list[list[float]]:
    return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _yaml_dump(data: dict) -> str:
    try:
        import yaml  # type: ignore

        return yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
    except ImportError:  # mini dump for the mini parser
        lines: list[str] = []

        def emit(d: dict, indent: int) -> None:
            for key, value in d.items():
                pad = "  " * indent
                if isinstance(value, dict):
                    lines.append(f"{pad}{key}:")
                    emit(value, indent + 1)
                elif isinstance(value, list):
                    lines.append(f"{pad}{key}:")
                    for item in value:
                        if isinstance(item, list):
                            lines.append(f"{pad}  - {_inline(item)}")
                        else:
                            lines.append(f"{pad}  - {item}")
                else:
                    lines.append(f"{pad}{key}: {value}")

        emit(data, 0)
        return "\n".join(lines) + "\n"


def _inline(items: list) -> str:
    return "[" + ", ".join(str(v) for v in items) + "]"