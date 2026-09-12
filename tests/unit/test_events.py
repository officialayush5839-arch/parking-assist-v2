"""EventBus publish/subscribe and history."""

from core.events import EventBus, EventType
from core.models import Severity


def test_publish_subscribe():
    bus = EventBus()
    got = []
    bus.subscribe(lambda e: got.append(e.event_type.value))
    bus.publish(EventType.SENSOR_TIMEOUT, Severity.WARNING, "sensor", {})
    assert got == ["SENSOR_TIMEOUT"]


def test_unsubscribe():
    bus = EventBus()
    got = []
    unsub = bus.subscribe(lambda e: got.append(e))
    bus.publish(EventType.CAMERA_STARTED, Severity.INFO, "camera", {})
    unsub()
    bus.publish(EventType.CAMERA_FAILURE, Severity.ERROR, "camera", {})
    assert len(got) == 1


def test_event_fields():
    bus = EventBus()
    event = bus.publish(EventType.SAFETY_STATE_CHANGED, Severity.INFO, "safety",
                        {"from": "SAFE", "to": "WARNING"})
    assert event.event_id > 0
    assert event.timestamp > 0
    d = event.to_dict()
    assert d["event_type"] == "SAFETY_STATE_CHANGED"
    assert d["payload"]["to"] == "WARNING"


def test_recent_history_bounded():
    bus = EventBus(history_size=10)
    for i in range(20):
        bus.publish(EventType.SYSTEM_STARTED, Severity.INFO, "test", {"i": i})
    assert len(bus.recent()) == 10


def test_listener_error_does_not_break_bus():
    bus = EventBus()

    def bad_listener(_e):
        raise RuntimeError("listener bug")

    bus.subscribe(bad_listener)
    bus.subscribe(lambda e: None)  # should still be called
    bus.publish(EventType.SYSTEM_STARTED, Severity.INFO, "test", {})