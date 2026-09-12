"""
Failure scenarios (integration, spec §41 scenarios 5–7):

5. Camera failure + valid ultrasonic ⇒ system continues on ultrasonic.
6. Ultrasonic failure + valid vision  ⇒ degraded operation with vision.
7. Both sensors invalid              ⇒ FAULT (configured degraded state).
"""

from core.models import Zone

from tests.conftest import SimTime


def test_camera_failure_continues_on_ultrasonic(camera_runtime):
    """No frames after t=2; ultrasonic still valid ⇒ states progress."""
    rt = camera_runtime
    clock = SimTime()
    dt = 1.0 / 15.0

    def detection_provider(now):
        return None  # camera dead ⇒ no vision ever

    rt.detector.set_mock_provider(detection_provider)
    # Sensor: approaches 3.0 → 0.8 m over 8 s.
    def sensor_provider(now):
        t = clock.t
        return (3.0 - 2.2 * min(1.0, t / 8.0), True)

    rt.sensor.set_provider(sensor_provider)
    rt.pipeline.reset()

    states = []
    while clock.t <= 8.0:
        reading = rt.sensor_reader.read()
        tel = rt.pipeline.step(
            frame=None, frame_id=int(clock.t * 15), frame_ts=clock.t,
            sensor_reading=reading, camera_healthy=False,
            predictor_note="deterministic_ttc")
        states.append(tel.state)
        clock.advance(dt)

    # Must keep working from ultrasonic alone and reach a warning state.
    assert Zone.CRITICAL in states or Zone.WARNING in states
    assert Zone.FAULT not in states


def test_ultrasonic_failure_continues_on_vision(camera_runtime):
    """Sensor invalid from t=1; vision valid ⇒ degraded CAUTION/WARNING."""
    rt = camera_runtime
    clock = SimTime()
    dt = 1.0 / 15.0

    from tests.conftest import detection_at

    def detection_provider(now):
        return [(d.class_name, d.confidence, d.bbox)
                for d in detection_at(_Approach(), clock.t, 0)]

    rt.detector.set_mock_provider(detection_provider)
    rt.sensor.set_provider(lambda now: (None, False))  # sensor dead
    rt.pipeline.reset()

    states = []
    while clock.t <= 8.0:
        reading = rt.sensor_reader.read()
        tel = rt.pipeline.step(frame=rt.camera.read(), frame_id=int(clock.t * 15),
                               frame_ts=clock.t, sensor_reading=reading,
                               camera_healthy=True, predictor_note="deterministic_ttc")
        states.append(tel.state)
        clock.advance(dt)

    assert Zone.CAUTION in states or Zone.WARNING in states
    assert Zone.FAULT not in states


def test_both_sources_invalid_is_fault(camera_runtime):
    rt = camera_runtime
    rt.detector.set_mock_provider(lambda now: None)
    rt.sensor.set_provider(lambda now: (None, False))
    rt.pipeline.reset()

    states = []
    for i in range(20):
        reading = rt.sensor_reader.read()
        tel = rt.pipeline.step(frame=None, frame_id=i, frame_ts=float(i),
                               sensor_reading=reading, camera_healthy=False,
                               predictor_note="deterministic_ttc")
        states.append(tel.state)
    assert states[-1] == Zone.FAULT


class _Approach:
    """Minimal stand-in so detection_at can map time → distance."""

    obj_width_m = 1.8

    def vision_distance(self, t):
        return 3.0 - 1.8 * min(1.0, t / 8.0)

    def vision_confidence(self, t):
        return 0.8

    def center_frac_x(self, t):
        return 0.5