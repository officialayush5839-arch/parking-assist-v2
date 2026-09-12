"""
dashboard/backend/server.py — Local diagnostics dashboard.

FastAPI backend exposing read-only monitoring endpoints plus a WebSocket
telemetry stream, and serving the HTML/JS frontend.  The dashboard is
monitoring only — it can never change the safety engine.
"""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import Any, Optional

from dashboard.backend.store import TelemetryStore

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


class DashboardServer:
    def __init__(self, store: TelemetryStore, host: str = "127.0.0.1",
                 port: int = 8765, cfg=None) -> None:
        self._store = store
        self._host = host
        self._port = port
        self._cfg = cfg
        self._thread: Optional[threading.Thread] = None
        self._server: Any = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run_uvicorn, name="dashboard", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            try:
                self._server.should_exit = True
            except Exception:
                pass

    # ── Internals ─────────────────────────────────────────────────────────────

    def _run_uvicorn(self) -> None:
        import uvicorn  # type: ignore  # noqa: PLC0415

        config = uvicorn.Config(
            self._create_app(), host=self._host, port=self._port,
            log_level="warning", access_log=False,
        )
        self._server = uvicorn.Server(config)
        asyncio.run(self._server.serve())

    def _create_app(self):
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # noqa: PLC0415
        from fastapi.middleware.cors import CORSMiddleware  # noqa: PLC0415
        from fastapi.staticfiles import StaticFiles  # noqa: PLC0415
        from pydantic import BaseModel  # noqa: PLC0415

        app = FastAPI(title="KPIT Parking Assist V2 — Diagnostics Dashboard")
        app.add_middleware(CORSMiddleware, allow_origins=["*"],
                           allow_methods=["*"], allow_headers=["*"])

        store = self._store

        @app.get("/api/health")
        def api_health() -> dict:
            return store.health()

        @app.get("/api/status")
        def api_status() -> dict:
            return {
                "telemetry": store.latest_telemetry(),
                "health": store.health(),
                "uptime_s": round(time.time() - _BOOT, 2),
            }

        @app.get("/api/metrics")
        def api_metrics() -> dict:
            return store.metrics()

        @app.get("/api/events")
        def api_events(limit: int = 100) -> list[dict]:
            return store.recent_events(min(limit, 500))

        @app.get("/api/config")
        def api_config() -> dict:
            return store.config()

        @app.get("/api/detections")
        def api_detections(limit: int = 50) -> list[dict]:
            return store.recent_detections(min(limit, 200))

        @app.get("/api/tracks")
        def api_tracks(limit: int = 50) -> list[dict]:
            return store.recent_tracks(min(limit, 200))

        @app.get("/api/safety")
        def api_safety() -> dict:
            return store.latest_safety()

        @app.websocket("/ws/telemetry")
        async def ws_telemetry(websocket: WebSocket) -> None:
            await websocket.accept()
            try:
                while True:
                    data = store.latest_telemetry()
                    if data is not None:
                        await websocket.send_json(data)
                    await asyncio.sleep(0.5)
            except WebSocketDisconnect:
                pass

        if FRONTEND_DIR.is_dir():
            app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True),
                      name="frontend")

        return app


_BOOT = time.time()