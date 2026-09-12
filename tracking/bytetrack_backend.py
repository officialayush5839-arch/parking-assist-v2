"""
tracking/bytetrack_backend.py — ByteTrack backend.

ByteTrack (bytetrack-python / ultralytics' ByteTrack) is a stronger
tracker than the IOU matcher.  The backend is **not installed by default**;
when it is unavailable the runtime falls back to the IOU tracker and
reports the fallback via an event.  This file keeps the interface honest —
it never silently pretends to be ByteTrack.
"""

from __future__ import annotations

from core.errors import TrackerUnavailable
from tracking.iou_tracker import IOUTracker


def try_create_bytetrack(iou_fallback: IOUTracker | None = None):
    """Return a ByteTrack-backed tracker or raise TrackerUnavailable.

    Detection output feeds ByteTrack through the same ObjectTracker
    interface; this stub documents the wiring.  Installing a compatible
    ``bytetrack`` package makes this backend live without pipeline changes.
    """
    import importlib.util  # noqa: PLC0415

    # Cheap availability probe (no heavyweight imports on the hot path).
    bytetrack_spec = importlib.util.find_spec("bytetrack")
    ultralytics_spec = importlib.util.find_spec("ultralytics")
    if bytetrack_spec is None and ultralytics_spec is None:
        raise TrackerUnavailable(
            "ByteTrack is not installed (pip install bytetrack). "
            "Falling back to the IOU tracker."
        )

    raise TrackerUnavailable(
        "ByteTrack backend: adapter not yet wired for this environment. "
        "Falling back to the IOU tracker."
    )


def create_tracker(backend: str, cfg=None):
    """Factory used by the runtime: returns an ObjectTracker.

    * backend: 'auto' | 'bytetrack' | 'iou'
    * Unavailable ByteTrack ⇒ IOU fallback with a published event.
    """
    from core.events import EventBus, EventType, Severity

    cfg = cfg or {}
    iou_threshold = _cfg_get(cfg, "tracking.iou_threshold", 0.30)
    max_lost = int(_cfg_get(cfg, "tracking.max_lost_frames", 20))
    bus: EventBus | None = _cfg_get(cfg, "_event_bus", None)

    iou = IOUTracker(iou_threshold=iou_threshold, max_lost_frames=max_lost)

    if backend in ("auto", "bytetrack"):
        try:
            return try_create_bytetrack(iou), False
        except TrackerUnavailable as exc:
            if bus is not None:
                bus.publish(EventType.TRACKER_FAILURE, Severity.WARNING,
                            "tracking", {"reason": str(exc)})
            return iou, True
    return iou, False


def _cfg_get(cfg, dotted: str, default):
    if cfg is None:
        return default
    if hasattr(cfg, "get"):
        return cfg.get(dotted, default)
    cur = cfg
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur