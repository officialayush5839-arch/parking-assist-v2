"""
app/pipeline.py — The V2 processing pipeline.

One call to :meth:`Pipeline.step` executes the full pipeline for a single
cycle:

    preprocess → detect → track → monocular distance → validate sensor
    → fusion → velocity → TTC → ML risk → deterministic safety

Every stage is timed by the MetricsCollector so FPS/latency are real
measurements.  The pipeline never blocks on I/O: logging/HMI are handled
by the runtime on a throttled cadence.
"""

from __future__ import annotations

import time
from typing import Optional

from acquisition.timestamp import now_wall
from camera.preprocessing import preprocess
from core.events import EventBus, EventType, Severity
from core.models import (
    Detection,
    DistanceEstimate,
    RiskAssessment,
    RiskClass,
    SensorReading,
    Telemetry,
    TrackedObject,
)
from diagnostics.metrics import MetricsCollector
from fusion.confidence_fusion import ConfidenceFusion
from ml.risk_prediction import RiskFeatures, RiskPredictor
from ml.ttc import compute_ttc
from tracking.tracker import ObjectTracker
from tracking.velocity import VelocityEstimator
from vision.detector import ObjectDetector
from zone.safety_engine import DeterministicSafetyEngine
from zone.thresholds import ZoneThresholds


class Pipeline:
    def __init__(self, detector: ObjectDetector, tracker: ObjectTracker,
                 monocular, fusion: ConfidenceFusion,
                 predictor: RiskPredictor, safety: DeterministicSafetyEngine,
                 thresholds: ZoneThresholds, cfg, event_bus: Optional[EventBus],
                 metrics: Optional[MetricsCollector] = None) -> None:
        self.detector = detector
        self.tracker = tracker
        self.monocular = monocular
        self.fusion = fusion
        self.predictor = predictor
        self.safety = safety
        self.thresholds = thresholds
        self.cfg = cfg
        self.bus = event_bus
        self.metrics = metrics or MetricsCollector()

        self._velocity = VelocityEstimator(
            ema_alpha=float(cfg.get("tracking.velocity.ema_alpha", 0.4)),
            max_plausible_mps=float(cfg.get("tracking.velocity.max_plausible_mps", 5.0)),
            history_s=float(cfg.get("tracking.velocity.history_s", 3.0)),
        )
        self._last_width: dict[int, int] = {}
        self._known_tracks: set[int] = set()
        self._last_detections: list[Detection] = []
        self._last_tracks: list[TrackedObject] = []
        self._cycle = 0
        self._low_light = False
        self._brightness = 128.0

    # ── Public API ────────────────────────────────────────────────────────────

    def step(self, frame, frame_id: int, frame_ts: float,
             sensor_reading: Optional[SensorReading],
             camera_healthy: bool = True,
             predictor_note: str = "") -> Telemetry:
        """Execute one full pipeline cycle; returns the cycle Telemetry."""
        cycle_start = time.perf_counter()
        self._cycle += 1
        now = now_wall()

        # ── Preprocess ────────────────────────────────────────────────────────
        self._stage("preprocess")
        vision_cfg = self.cfg.get("vision", {})
        processed = preprocess(
            frame,
            target_size=(int(vision_cfg.get("input_width", 640)),
                         int(vision_cfg.get("input_height", 480))),
            denoise=bool(vision_cfg.get("denoise", False)),
            low_light_threshold=int(self.cfg.get("camera.low_light_threshold", 40)),
        )
        self._low_light = processed.low_light
        self._brightness = processed.brightness
        self._stage_end()

        # ── Detect ────────────────────────────────────────────────────────────
        self._stage("detect")
        detections = self.detector.detect(processed.frame, frame_ts, frame_id)
        self._stage_end()

        # ── Track ─────────────────────────────────────────────────────────────
        self._stage("track")
        tracks = self.tracker.update(detections, frame_ts)
        self._publish_track_lifecycle(tracks)
        self._stage_end()

        # ── Monocular distance per track ──────────────────────────────────────
        self._stage("vision_distance")
        calibration_ok = getattr(self.monocular, "calibration_available", False)
        frame_w, frame_h = _frame_size(frame)
        track_estimates: list[tuple[TrackedObject, DistanceEstimate]] = []
        primary_est: Optional[DistanceEstimate] = None
        for track in tracks:
            det = Detection(track.class_name, track.confidence, track.bbox,
                            frame_ts, frame_id)
            prev_w = self._last_width.get(track.track_id)
            est = self.monocular.estimate(det, calibration_ok, frame_w, frame_h,
                                          prev_width_px=prev_w)
            self._last_width[track.track_id] = track.width_px if hasattr(track, "width_px") else (track.bbox[2] - track.bbox[0])
            track.estimated_distance = est.distance_m
            track_estimates.append((track, est))
            if est.valid and (primary_est is None
                              or (est.distance_m or 1e9) < (primary_est.distance_m or 1e9)):
                primary_est = est
        self._prune_last_width(tracks)
        self._stage_end()

        # ── Fusion ────────────────────────────────────────────────────────────
        self._stage("fusion")
        fusion = self.fusion.fuse(sensor_reading, primary_est, now)
        if fusion.disagreement and self.bus is not None:
            self.bus.publish(EventType.SENSOR_DISAGREEMENT, Severity.WARNING,
                             "fusion", {"sensor_m": fusion.sensor_distance,
                                        "vision_m": fusion.vision_distance})
        self._stage_end()

        # ── Velocity + TTC (deterministic kinematics) ─────────────────────────
        self._stage("velocity")
        closing_speed = self._velocity.update(0, fusion.fused_distance_m, now)
        ttc = compute_ttc(fusion.fused_distance_m, closing_speed).ttc_seconds
        self._stage_end()

        # ── ML / advisory risk ────────────────────────────────────────────────
        self._stage("risk")
        features = RiskFeatures(
            distance_m=fusion.fused_distance_m,
            closing_speed_mps=closing_speed,
            ttc_seconds=ttc,
            detector_confidence=_max_det_conf(detections),
            tracker_confidence=primary_est.confidence if primary_est else None,
            sensor_confidence=fusion.confidence,
            disagreement=fusion.disagreement,
            class_name=primary_track_class(tracks, primary_est),
        )
        try:
            risk = self.predictor.predict(features)
            risk.timestamp = now
        except Exception:
            risk = RiskAssessment(0.0, RiskClass.LOW, 0.0, "error", now)
        self._stage_end()

        # ── Deterministic safety decision ─────────────────────────────────────
        self._stage("decision")
        decision = self.safety.evaluate(
            fusion=fusion,
            sensor=sensor_reading,
            vision=primary_est,
            risk=risk,
            closing_speed_mps=closing_speed,
            now=now,
        )
        self._stage_end()

        self._last_detections = detections
        self._last_tracks = tracks

        # ── Telemetry ─────────────────────────────────────────────────────────
        latency_ms = (time.perf_counter() - cycle_start) * 1000.0
        self.metrics.cycle_end(latency_ms)
        telemetry = Telemetry(
            cycle_id=self._cycle,
            timestamp=now,
            state=decision.state,
            distance_m=decision.distance_m,
            confidence=decision.confidence,
            object_class=primary_track_class(tracks, primary_est),
            closing_speed_mps=decision.closing_speed_mps,
            ttc_seconds=decision.ttc_seconds,
            risk_score=decision.risk_score,
            fps=self.metrics.fps(),
            latency_ms=latency_ms,
            detections=len(detections),
            tracks=len(tracks),
            reason_codes=list(decision.reason_codes),
            verbose={
                "camera": "OK" if camera_healthy else "FAULT",
                "sensor": "OK" if (sensor_reading and sensor_reading.valid) else "FAULT",
                "ml": predictor_note or self.predictor.name(),
                "low_light": self._low_light,
                "brightness": round(self._brightness, 1),
                "detections": [d.class_name for d in detections],
                "method": fusion.method,
            },
        )
        return telemetry

    def reset(self) -> None:
        self.tracker.reset()
        self._velocity.reset()
        self._last_width.clear()
        self._known_tracks.clear()
        self.safety.reset()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _stage(self, name: str) -> None:
        self.metrics.stage_begin(name)

    def _stage_end(self) -> None:
        self.metrics.stage_end()

    def _publish_track_lifecycle(self, tracks: list[TrackedObject]) -> None:
        if self.bus is None:
            return
        current = {t.track_id for t in tracks}
        for track_id in current - self._known_tracks:
            self.bus.publish(EventType.TRACK_CREATED, Severity.INFO, "tracking",
                             {"track_id": track_id})
        self._known_tracks = current

    def _prune_last_width(self, tracks: list[TrackedObject]) -> None:
        active = {t.track_id for t in tracks}
        stale = [tid for tid in self._last_width if tid not in active]
        for tid in stale:
            self._last_width.pop(tid, None)
            self._velocity.remove(tid)


def _frame_size(frame) -> tuple[int, int]:
    if frame is None:
        return 640, 480
    h, w = frame.shape[:2]
    return int(w), int(h)


def _max_det_conf(detections: list[Detection]) -> Optional[float]:
    return max((d.confidence for d in detections), default=None)


def primary_track_class(tracks: list[TrackedObject],
                        primary_est: Optional[DistanceEstimate]) -> Optional[str]:
    if not tracks or primary_est is None:
        return tracks[0].class_name if tracks else None
    best, best_d = None, 1e9
    for t in tracks:
        d = t.estimated_distance or 1e9
        if d < best_d:
            best, best_d = t, d
    return best.class_name if best else None


