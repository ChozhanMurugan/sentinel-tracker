"""
SENTINEL Backend — FastAPI application entry point.
Handles startup/shutdown lifecycle, middleware, and route registration.
"""
from __future__ import annotations
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.scheduler import scheduler, setup as scheduler_setup
from app.services import ais
from app.api.routes import aircraft, ships, stats, websocket

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


# ── App factory ───────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="SENTINEL Backend",
        version="1.0.0",
        description="Real-time flight, ship & military aircraft tracking API",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ──────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ────────────────────────────────────────────────
    app.include_router(aircraft.router)
    app.include_router(ships.router)
    app.include_router(stats.router)
    app.include_router(websocket.router)

    # ── Lifecycle ─────────────────────────────────────────────
    @app.on_event("startup")
    async def on_startup():
        log.info("▶ SENTINEL backend starting up …")

        # Start APScheduler (OpenSky poll + stats broadcast)
        scheduler_setup(app)
        scheduler.start()
        log.info("⏱  Scheduler started — polling OpenSky every %ds",
                 settings.OPENSKY_REFRESH_S)

        # Start AIS relay as a background task
        if settings.AIS_KEY:
            asyncio.create_task(ais.run(), name="ais_relay")
            log.info("🚢 AIS relay started")
        else:
            log.warning("⚠  AIS_KEY not set — ship tracking disabled")

        # Run first OpenSky poll immediately (don't wait for first interval)
        from app.services.opensky import poll
        asyncio.create_task(poll(), name="opensky_initial")

        log.info("✅ SENTINEL backend ready at http://%s:%d",
                 settings.BACKEND_HOST, settings.BACKEND_PORT)

    @app.on_event("shutdown")
    async def on_shutdown():
        scheduler.shutdown(wait=False)
        log.info("🛑 SENTINEL backend shutdown complete")

    # ── Health check ──────────────────────────────────────────
    @app.get("/health", tags=["system"])
    async def health():
        from app.redis_client import redis as r
        try:
            await r.ping()
            redis_ok = True
        except Exception:
            redis_ok = False
        return {
            "status": "ok",
            "redis":  "ok" if redis_ok else "unavailable",
            "docs":   "/docs",
        }

    return app


app = create_app()
