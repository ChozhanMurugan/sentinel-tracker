"""
API routes — REST endpoints + WebSocket for the ML service.
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..anomaly import AnomalyDetector
from ..broadcaster import Broadcaster
from ..classifier import classify
from ..collector import Collector

router = APIRouter()

# These are injected at app startup via main.py
collector: Collector | None = None
detector: AnomalyDetector | None = None
broadcaster: Broadcaster | None = None
_latest_anomalies: list[dict] = []


def set_services(c: Collector, d: AnomalyDetector, b: Broadcaster):
    global collector, detector, broadcaster
    collector = c
    detector = d
    broadcaster = b


def set_latest_anomalies(anomalies: list[dict]):
    global _latest_anomalies
    _latest_anomalies = anomalies


# ── REST ──────────────────────────────────────────────────────────

@router.get("/api/anomalies")
async def get_anomalies():
    """Current anomalous aircraft with scores and reasons."""
    return {
        "count": len(_latest_anomalies),
        "anomalies": _latest_anomalies,
    }


@router.get("/api/classify/{icao24}")
async def classify_aircraft(icao24: str, callsign: str = ""):
    """Classify a single aircraft as military or civilian."""
    result = classify(icao24, callsign)
    return {
        "icao24": icao24,
        "callsign": callsign,
        "military": result.military,
        "confidence": result.confidence,
        "method": result.method,
        "label": result.label,
    }


@router.get("/api/stats")
async def get_stats():
    """ML service status."""
    return {
        "collector": collector.stats if collector else {},
        "detector": detector.stats if detector else {},
        "ws_clients": broadcaster.client_count if broadcaster else 0,
        "anomaly_count": len(_latest_anomalies),
    }


@router.get("/health")
async def health():
    return {"status": "ok", "service": "sentinel-ml"}


# ── WebSocket ─────────────────────────────────────────────────────

@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    if broadcaster is None:
        await ws.close()
        return
    await broadcaster.connect(ws)
    try:
        # Send current anomalies on connect
        await ws.send_json({
            "type": "snapshot",
            "anomalies": _latest_anomalies,
        })
        # Keep alive — listen for pings / client messages
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        broadcaster.disconnect(ws)
    except Exception:
        broadcaster.disconnect(ws)
