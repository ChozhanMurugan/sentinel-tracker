"""
SENTINEL-ML — FastAPI entry point.
Starts the data collector and anomaly detection loop on startup.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .anomaly import AnomalyDetector
from .broadcaster import Broadcaster
from .classifier import classify as classify_heuristic
from .collector import Collector
from .config import settings
from .features import extract_all
from .api.routes import router, set_services, set_latest_anomalies

# ── Shared instances ──────────────────────────────────────────────
collector = Collector()
detector = AnomalyDetector()
broadcaster = Broadcaster()


async def _analysis_loop():
    """Runs after each poll — extracts features, trains/scores, broadcasts anomalies."""
    while True:
        await asyncio.sleep(settings.poll_interval_s + 1)  # offset from poll

        buf = collector.get_buffer()
        if not buf:
            continue

        # Extract features
        features = extract_all(buf)
        if not features:
            continue

        # Attempt to fit/refit
        detector.maybe_fit(features)

        # Score
        results = detector.score(features)
        if not results:
            continue

        # Build anomaly list
        latest = collector.get_latest()
        anomalies: list[dict] = []
        for r in results:
            if not r.is_anomaly:
                continue
            snap = latest.get(r.icao24)
            if not snap:
                continue

            # Also run classifier
            cls = classify_heuristic(r.icao24, snap.callsign)

            anomalies.append({
                "icao24": r.icao24,
                "callsign": snap.callsign,
                "lat": snap.lat,
                "lon": snap.lon,
                "altitude": snap.altitude,
                "speed": snap.speed,
                "heading": snap.heading,
                "country": snap.country,
                "anomaly_score": round(r.score, 4),
                "reasons": r.reasons,
                "military": cls.military,
                "mil_confidence": round(cls.confidence, 2),
                "mil_method": cls.method,
                "mil_label": cls.label,
            })

        set_latest_anomalies(anomalies)

        # Broadcast to connected clients
        if anomalies:
            await broadcaster.broadcast({
                "type": "anomalies",
                "count": len(anomalies),
                "anomalies": anomalies,
            })
            print(f"[ML] {len(anomalies)} anomalies broadcast to {broadcaster.client_count} clients")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background tasks on startup, clean up on shutdown."""
    set_services(collector, detector, broadcaster)

    # Launch background tasks
    collector_task = asyncio.create_task(collector.start())
    analysis_task = asyncio.create_task(_analysis_loop())

    print(f"[ML] SENTINEL-ML started on port {settings.port}")
    yield

    # Shutdown
    collector.stop()
    collector_task.cancel()
    analysis_task.cancel()
    print("[ML] SENTINEL-ML stopped")


# ── App ───────────────────────────────────────────────────────────
app = FastAPI(
    title="SENTINEL ML Intelligence",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
