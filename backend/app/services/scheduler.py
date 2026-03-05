"""
APScheduler setup — runs recurring background jobs inside FastAPI's async loop.
No Celery required for this scale.
"""
from __future__ import annotations
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.services import opensky

log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


def setup(app) -> None:
    """Register all recurring jobs."""

    # ── OpenSky poll ──────────────────────────────────────────
    scheduler.add_job(
        opensky.poll,
        trigger=IntervalTrigger(seconds=settings.OPENSKY_REFRESH_S),
        id="opensky_poll",
        name="OpenSky aircraft poll",
        replace_existing=True,
        max_instances=1,          # never overlap
        misfire_grace_time=30,
    )

    # ── Stats broadcast (every 30s) ───────────────────────────
    from app.services import stats as stats_svc
    scheduler.add_job(
        stats_svc.broadcast_stats,
        trigger=IntervalTrigger(seconds=30),
        id="stats_broadcast",
        name="Broadcast live stats",
        replace_existing=True,
    )

    log.info("Scheduler configured: OpenSky every %ds, stats every 30s",
             settings.OPENSKY_REFRESH_S)
