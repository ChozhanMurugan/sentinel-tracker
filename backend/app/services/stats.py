"""
Live stats service — computes counts from Redis and broadcasts to WS clients.
"""
from __future__ import annotations
import json
import logging
import time

from app.redis_client import redis
from app.services.broadcaster import manager

log = logging.getLogger(__name__)


async def get_counts() -> dict:
    """Compute live contact counts from Redis."""
    commercial, military, ships = 0, 0, 0
    try:
        all_aircraft = await redis.hvals("aircraft")
        for raw in all_aircraft:
            data = json.loads(raw)
            if data.get("mil"):
                military += 1
            else:
                commercial += 1

        ships = await redis.hlen("ships")
    except Exception as exc:
        log.error("Stats error: %s", exc)

    return {
        "commercial": commercial,
        "military": military,
        "ships": ships,
        "total": commercial + military + ships,
    }


async def broadcast_stats() -> None:
    """Broadcast current stats to all WS clients."""
    counts = await get_counts()
    if manager.count > 0:
        await manager.broadcast({
            "type": "stats",
            **counts,
        })
