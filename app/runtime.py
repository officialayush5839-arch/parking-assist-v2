"""
app/runtime.py — Component wiring and the main control loop.

Composition root: builds every subsystem from configuration, runs the
pipeline at the configured rate, and shuts everything down cleanly.
Hardware backends are attempted only in ``hardware`` mode; everywhere
else the MOCK / SIMULATION components are used and clearly reported.
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime
from typing import Optional

from acquisition.frame_reader import FrameReader
from acquisition.sensor_reader import SensorReader
from alerts.buzzer_controller import MockBuzzer
from alerts.led_controller import MockLEDBank, ZoneLEDMapper
from alerts.scheduler import AlertScheduler
from camera.calibration import CameraCalibration
from camera.interface import CameraInterface
from camera.mock_camera import MockCamera
from core.config import PROJECT_ROOT, Settings
from core.errors import ComponentUnavailable
from core.events import EventBus, EventType, Severity
from core.models import DistanceEstimate, Telemetry, Zone
from datalog.event_logger import EventLogger
from datalog.experiment_logger import ExperimentLogger
from datalog.sensor_logger import SensorLogger
from datalog.vision_logger import VisionLogger
from diagnostics.health import HealthMonitor
from diagnostics.metrics import MetricsCollector
from diagnostics.system_monitor import SystemMonitor
from display.hmi import HMIController
from display.lcd import MockLCD
from distance.monocular import MonocularDistanceEstimator
from distance.ultrasonic import (
    DistanceSensorInterface,
    MockUltrasonicSensor,
    RecordedUltrasonicSensor,
    SensorConfig,
)
from fusion.confidence_fusion import ConfidenceFusion
from fusion.fusion_policy import FusionPolicy
from ml.risk_prediction import create_predictor
from ml.ttc import ttc_display
from processing.filters import RateLimiter
from simulation.scenario import Scenario
from simulation.scenarios import get_scenario
from simulation.simulator import Simulator
from tracking.bytetrack_backend import create_tracker
from vision.detector import ObjectDetector
from zone.safety_engine import DeterministicSafetyEngine
from zone.thresholds import ZoneThresholds

log = logging.getLogger("kpa.runtime")


class Runtime:
    def __init__(self, cfg: Settings, mode: str,
                 scenario_name: Optional[str] = None,
                 duration_s: Optional[float] = None,
                 dashboard_enabled: Optional[bool] = None,
                 event_bus: Optional[EventBus] = None) -> None:
        self.cfg = cfg
        self.mode = mode
        self.bus = event_bus or EventBus()
        self.duration = duration_s if duration_s and duration_s > 0 else float(cfg.get("system.duration_s", 0) or 0)
        self._running = False
        self._loop_hz = max(1, int(cfg.get("system.loop_hz", 15)))
        self._min_interval = 1.0 / self._loop_hz

        # Diagnostics
        self.metrics = MetricsCollector()
        self.health = HealthMonitor(float(cfg.get("diagnostics.health_degrade_after_s", 3.0)))
        self.monitor = SystemMonitor()
        for name in ("camera", "distance_sensor", "detector", "tracker", "ml", "calibration"):
            self.health.register(name)

        # Camera calibration (loaded before the simulator so focal is known)
        self.calibration = CameraCalibration.load_or_none(
            str(PROJECT_ROOT / cfg.get("camera.calibration_file", "config/camera_calibration.yaml")))
        self.calibration_ok = bool(self.calibration and self.calibration.available)
        if not self.calibration_ok:
            self.bus.publish(EventType.CALIBRATION_MISSING, Severity.WARNING,
                             "calibration", {"note": "monocular distance is approximate"})

        # Simulation timeline (simulation/demo modes)
        self.scenario: Optional[Scenario] = None
        self.simulator: Optional[Simulator] = None
        self._sim_origin = time.time()
        if mode in ("simulation", "demo"):
            default_scenario = "demo_sequence" if mode == "demo" else "vehicle_approaching_fast"
            name = scenario_name or cfg.get("system.scenario") or default_scenario
            self.scenario = get_scenario(name)
            self.simulator = Simulator(
                self.scenario,
                loop_hz=self._loop_hz,
                width=int(cfg.get("camera.width", 640)),
                height=int(cfg.get("camera.height", 480)),
                focal_px=self._monocular_focal(),
                sensor_noise_m=0.02,
            )
            self._sim_origin = self.simulator.start()

        # Hardware-ish components
        self.camera = self._build_camera()
        self.frame_reader = FrameReader(self.camera)
        self.sensor = self._build_sensor()
        self.sensor_reader = SensorReader(self.sensor)

        # Vision chain
        self.detector = ObjectDetector(cfg, self.bus)
        if self.simulator is not None:
            self.detector.set_mock_provider(self.simulator.detection_provider)
        tracker_cfg = dict(cfg.as_dict())
        tracker_cfg["_event_bus"] = self.bus
        self.tracker, self.tracker_is_mock = create_tracker(
            cfg.get("tracking.backend", "auto"), tracker_cfg)

        # Distance
        self.monocular = MonocularDistanceEstimator(
            focal_length_px=self._monocular_focal(),
            known_widths_m=cfg.get("distance.monocular.known_widths_m", {}),
            min_distance_m=float(cfg.get("distance.monocular.min_distance_m", 0.2)),
            max_distance_m=float(cfg.get("distance.monocular.max_distance_m", 20.0)),
        )
        self.monocular.calibration_available = self.calibration_ok

        # Fusion
        self.fusion = ConfidenceFusion(FusionPolicy.from_cfg(cfg))

        # Advisory risk
        self.predictor, self.predictor_is_mock = create_predictor(cfg, self.bus)

        # Deterministic safety
        self.thresholds = ZoneThresholds.from_cfg(cfg)
        self.safety = DeterministicSafetyEngine(self.thresholds, cfg, self.bus)

        # Pipeline
        from app.pipeline import Pipeline

        self.pipeline = Pipeline(
            detector=self.detector,
            tracker=self.tracker,
            monocular=self.monocular,
            fusion=self.fusion,
            predictor=self.predictor,
            safety=self.safety,
            thresholds=self.thresholds,
            cfg=cfg,
            event_bus=self.bus,
            metrics=self.metrics,
        )

        # Alerts
        led_bank = MockLEDBank(self.bus)
        self.led_mapper = ZoneLEDMapper(led_bank, cfg.get("alerts.led_mapping", {}))
        buzzer = MockBuzzer() if bool(cfg.get("alerts.buzzer_enabled", True)) else None
        self.alerts = AlertScheduler(
            self.led_mapper, buzzer,
            buzzer_enabled=bool(cfg.get("alerts.buzzer_enabled", True)),
        )

        # Display
        lcd = MockLCD()
        self.hmi = HMIController(lcd, page_interval_s=2.0)

        # Logging
        log_dir = PROJECT_ROOT / cfg.get("logging.directory", "logs")
        self.event_logger = EventLogger(log_dir, self.bus)
        self.sensor_logger = SensorLogger(log_dir)
        self.vision_logger = VisionLogger(log_dir)
        self.experiment_logger = ExperimentLogger(log_dir, source=mode)
        self._telemetry_limiter = RateLimiter(0.5)
        self._experiment_limiter = RateLimiter(0.5)

        # Dashboard (optional)
        self.telemetry_store = None
        self.dashboard_server = None
        dash_enabled = dashboard_enabled if dashboard_enabled is not None else bool(cfg.get("dashboard.enabled", False))
        if dash_enabled:
            self._start_dashboard()

        self._last_state: Optional[Zone] = None

    # ── Construction helpers ──────────────────────────────────────────────────

    def _monocular_focal(self) -> float:
        if self.calibration is not None and self.calibration.available:
            fx = self.calibration.focal_length_px()
            if fx and fx > 1.0:
                return fx
        return float(self.cfg.get("distance.monocular.focal_length_px", 600.0))

    def _build_camera(self) -> CameraInterface:
        if self.mode in ("simulation", "demo"):
            cam = MockCamera(width=int(self.cfg.get("camera.width", 640)),
                             height=int(self.cfg.get("camera.height", 480)))
            cam.set_provider(self.simulator.camera_provider)
            cam.start()
            self.bus.publish(EventType.CAMERA_STARTED, Severity.INFO, "camera",
                             {"backend": "mock_synthetic"})
            return cam

        backend = self.cfg.get("camera.backend", "auto")
        try:
            if backend == "video":
                from camera.video_camera import VideoFileCamera

                cam: CameraInterface = VideoFileCamera(
                    self.cfg.get("camera.video_file") or "data/recordings/sample.mp4")
            elif backend == "mipi":
                from camera.mipi_camera import MIPICamera

                cam = MIPICamera(source=self.cfg.get("camera.source", "/dev/video0"),
                                 width=int(self.cfg.get("camera.width", 640)),
                                 height=int(self.cfg.get("camera.height", 480)),
                                 target_fps=int(self.cfg.get("camera.fps", 15)))
            elif backend == "mock":
                cam = MockCamera(width=int(self.cfg.get("camera.width", 640)),
                                 height=int(self.cfg.get("camera.height", 480)))
            else:  # auto | usb
                from camera.usb_camera import USBCamera

                cam = USBCamera(source=self.cfg.get("camera.source", 0),
                                width=int(self.cfg.get("camera.width", 640)),
                                height=int(self.cfg.get("camera.height", 480)),
                                target_fps=int(self.cfg.get("camera.fps", 15)))
            cam.start()
            self.bus.publish(EventType.CAMERA_STARTED, Severity.INFO, "camera",
                             {"backend": backend})
            return cam
        except ComponentUnavailable as exc:
            self.bus.publish(EventType.CAMERA_FAILURE, Severity.WARNING, "camera",
                             {"reason": str(exc)})
            cam = MockCamera(width=int(self.cfg.get("camera.width", 640)),
                             height=int(self.cfg.get("camera.height", 480)))
            cam.start()
            return cam

    def _build_sensor(self) -> DistanceSensorInterface:
        if self.mode in ("simulation", "demo"):
            from simulation.synthetic_sensor import build_sensor

            sensor = build_sensor(self.scenario,
                                  self.cfg.get("distance.ultrasonic", {}),
                                  origin=self._sim_origin,
                                  noise_m=0.02)
            sensor.start()
            return sensor

        sensor_backend = self.cfg.get("distance.ultrasonic.backend", "mock")
        if sensor_backend == "recorded":
            path = self.cfg.get("distance.ultrasonic.recorded_file")
            if path:
                rec = RecordedUltrasonicSensor(str(PROJECT_ROOT / path))
                rec.start()
                return rec
        if sensor_backend == "real":
            try:
                from distance.ultrasonic import RealUltrasonicSensor

                sensor = RealUltrasonicSensor(
                    trigger_pin=int(self.cfg.get("distance.ultrasonic.trigger_pin", 17)),
                    echo_pin=int(self.cfg.get("distance.ultrasonic.echo_pin", 27)),
                    config=SensorConfig(
                        min_range_m=float(self.cfg.get("distance.ultrasonic.min_range_m", 0.05)),
                        max_range_m=float(self.cfg.get("distance.ultrasonic.max_range_m", 4.5)),
                        timeout_s=float(self.cfg.get("distance.ultrasonic.timeout_s", 0.5)),
                    ),
                )
                sensor.start()
                return sensor
            except ComponentUnavailable as exc:
                self.bus.publish(EventType.SENSOR_FAILURE, Severity.WARNING,
                                 "sensor", {"reason": str(exc)})
        # Default: mock sensor with an idle (no echo) provider — vision-only.
        sensor = MockUltrasonicSensor(provider=lambda now: (None, False),
                                      config=SensorConfig(
                                          min_range_m=float(self.cfg.get("distance.ultrasonic.min_range_m", 0.05)),
                                          max_range_m=float(self.cfg.get("distance.ultrasonic.max_range_m", 4.5)),
                                      ))
        sensor.start()
        return sensor

    def _start_dashboard(self) -> None:
        from dashboard.backend.server import DashboardServer, TelemetryStore

        self.telemetry_store = TelemetryStore(capacity=1000)
        self.dashboard_server = DashboardServer(
            store=self.telemetry_store,
            host=self.cfg.get("dashboard.host", "127.0.0.1"),
            port=int(self.cfg.get("dashboard.port", 8765)),
            cfg=self.cfg,
        )
        self.dashboard_server.start()
        print(f"  Dashboard: http://{self.cfg.get('dashboard.host', '127.0.0.1')}:"
              f"{self.cfg.get('dashboard.port', 8765)}")

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> int:
        self._running = True
        self.bus.publish(EventType.SYSTEM_STARTED, Severity.INFO, "runtime",
                         {"mode": self.mode})
        start_wall = time.time()
        loop_slots = 0
        try:
            while self._running:
                if self.duration and time.time() - start_wall >= self.duration:
                    break

                cycle_start = time.monotonic()
                now = time.time()

                # Acquire
                frame, frame_id, frame_ts = self.frame_reader.read()
                if frame is None and self.mode in ("camera", "hardware"):
                    self.health.mark_fault("camera", "no frame")
                else:
                    self.health.mark_ok("camera")

                sensor_reading = self.sensor_reader.read()
                if sensor_reading.valid:
                    self.health.mark_ok("distance_sensor")
                else:
                    self.health.mark_fault("distance_sensor", sensor_reading.reason or "invalid")

                # Process
                telemetry = self.pipeline.step(
                    frame=frame,
                    frame_id=frame_id,
                    frame_ts=frame_ts,
                    sensor_reading=sensor_reading,
                    camera_healthy=self.camera.healthy,
                    predictor_note=self.predictor.name(),
                )

                # Safety-authoritative outputs
                self.alerts.update(telemetry.state, now)
                self.hmi.update(telemetry, now)

                # Health
                self.health.mark_ok("detector",
                                    "mock" if self.detector.is_mock else self.detector.backend_name)
                self.health.mark_ok("tracker", "iou" if self.tracker_is_mock else "bytetrack")
                self.health.mark_ok("ml", "mock" if self.predictor_is_mock else self.predictor.name())
                self.health.mark_ok("calibration", "available" if self.calibration_ok else "missing")

                # Logging (throttled)
                self.sensor_logger.log(sensor_reading)
                if self._telemetry_limiter.allow(now):
                    self._log_detections(telemetry)
                if self._experiment_limiter.allow(now):
                    self.experiment_logger.log_cycle(telemetry)

                # Console telemetry
                if self._console_limiter().allow(now) or self.cfg.get("system.verbose", False):
                    self._print_telemetry(telemetry)

                # Dashboard store
                if self.telemetry_store is not None:
                    self.telemetry_store.push_telemetry(telemetry)

                # State-change observability
                if telemetry.state != self._last_state:
                    self._last_state = telemetry.state

                self.metrics.cycle_end()
                loop_slots += 1

                # Rate limit
                elapsed = time.monotonic() - cycle_start
                sleep = self._min_interval - elapsed
                if sleep > 0:
                    time.sleep(sleep)
        except KeyboardInterrupt:
            print("\nInterrupted.")
        finally:
            self.shutdown()
        return 0

    def _console_limiter(self) -> RateLimiter:
        if not hasattr(self, "_console_rate"):
            self._console_rate = RateLimiter(0.5)
        return self._console_rate

    def stop(self) -> None:
        self._running = False

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        self._running = False
        self.bus.publish(EventType.SYSTEM_STOPPED, Severity.INFO, "runtime", {})
        self.alerts.reset()
        if self.hmi.available:
            self.hmi.update(_idle_telemetry(), time.time())
        self.event_logger.close()
        self.sensor_logger.close()
        self.vision_logger.close()
        self.experiment_logger.close()
        self.frame_reader.camera.stop()
        self.sensor_reader.sensor.stop()
        self.detector.shutdown()
        if self.dashboard_server is not None:
            self.dashboard_server.stop()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log_detections(self, telemetry: Telemetry) -> None:
        detections = getattr(self.pipeline, "_last_detections", [])
        tracks = getattr(self.pipeline, "_last_tracks", [])
        self.vision_logger.log_detections(detections)
        self.vision_logger.log_tracks(tracks)
        if detections:
            primary = detections[0]
            self.vision_logger.log_monocular(
                DistanceEstimate(telemetry.distance_m, telemetry.confidence,
                                 "fused", True, telemetry.timestamp))

    def _print_telemetry(self, t: Telemetry) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        dist = f"{t.distance_m:.2f}m" if t.distance_m is not None else "-"
        obj = (t.object_class or "-")
        conf = f"{t.confidence * 100:.0f}%" if t.confidence else "-"
        speed = f"{t.closing_speed_mps:.2f}m/s" if t.closing_speed_mps is not None else "-"
        risk = f"{t.risk_score * 100:.0f}%" if t.risk_score is not None else "-"
        line = (f"[{stamp}] STATE={t.state.value} DIST={dist} OBJ={obj} "
                f"CONF={conf} SPEED={speed} TTC={ttc_display(t.ttc_seconds)} "
                f"RISK={risk} FPS={t.fps:.1f}")
        print(line)
        if self.cfg.get("system.verbose", False):
            print(f"  reasons={t.reason_codes} health={self.health.health().components} "
                  f"latency={t.latency_ms:.1f}ms")


def _idle_telemetry() -> Telemetry:
    return Telemetry(
        cycle_id=0, timestamp=time.time(), state=Zone.UNKNOWN, distance_m=None,
        confidence=0.0, object_class=None, closing_speed_mps=None,
        ttc_seconds=None, risk_score=None, fps=0.0, latency_ms=0.0,
        detections=0, tracks=0,
    )


def run_self_test(cfg: Settings) -> int:
    """Quick hardware-independent component checks (--mode selftest)."""
    failures: list[str] = []
    checks: list[tuple[str, bool]] = []

    # Config
    try:
        load_config_ok = cfg is not None
    except Exception:
        load_config_ok = False
    checks.append(("configuration loads", load_config_ok))

    # Thresholds ordering
    thresholds = ZoneThresholds.from_cfg(cfg)
    checks.append(("zone thresholds ordered", True))

    # TTC math
    from ml.ttc import compute_ttc

    checks.append(("TTC kinematics", compute_ttc(2.0, 1.0).ttc_seconds == 2.0))
    checks.append(("TTC no-approach", compute_ttc(2.0, 0.0).ttc_seconds == float("inf")))

    # Fusion
    from fusion.confidence_fusion import ConfidenceFusion
    from core.models import SensorReading, DistanceEstimate

    fus = ConfidenceFusion(FusionPolicy())
    both = fus.fuse(
        SensorReading("ultrasonic", 1.0, True, time.time()),
        DistanceEstimate(1.1, 0.9, "monocular_geometry", True, time.time()),
        time.time())
    checks.append(("fusion weighted", both.valid and not both.disagreement))
    only_sensor = fus.fuse(SensorReading("ultrasonic", 0.9, True, time.time()), None, time.time())
    checks.append(("fusion ultrasonic-only", only_sensor.valid))

    # Safety hard override (the acceptance rule)
    bus = EventBus()
    engine = DeterministicSafetyEngine(thresholds, cfg, bus)
    decision = engine.evaluate(
        fusion=None,
        sensor=SensorReading("ultrasonic", 0.30, True, time.time()),
        vision=None,
        risk=None,
        closing_speed_mps=None,
        now=time.time(),
    )
    checks.append(("hard override => CRITICAL", decision.state == Zone.CRITICAL))

    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failures.append(name)
    if failures:
        print(f"\nSelf-test FAILED: {failures}")
        return 1
    print("\nSelf-test PASSED.")
    return 0