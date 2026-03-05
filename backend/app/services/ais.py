"""
aisstream.io WebSocket relay.
Connects as a WebSocket client to aisstream.io, decodes AIS position reports,
stores to TimescaleDB, updates Redis, and broadcasts to frontend clients.
"""
from __future__ import annotations
import asyncio
import json
import logging
import time
from datetime import datetime, timezone

import websockets

from app.config import settings
from app.redis_client import redis
from app.services.broadcaster import manager
from app.database import AsyncSessionLocal
from app.models.ship import ShipPosition

log = logging.getLogger(__name__)

_AIS_URL  = "wss://stream.aisstream.io/v0/stream"

# AIS message types we care about
_POSITION_TYPES = {"PositionReport", "StandardClassBPositionReport"}


def _parse_ais(msg: dict) -> dict | None:
    """Parse an AISStream message into a clean ship dict."""
    try:
        msg_type = msg.get("MessageType", "")
        if msg_type not in _POSITION_TYPES:
            return None

        meta = msg.get("MetaData", {})
        pos  = msg.get("Message", {}).get(msg_type, {})

        mmsi    = str(meta.get("MMSI", "")).strip()
        lat     = meta.get("latitude") or pos.get("Latitude")
        lon     = meta.get("longitude") or pos.get("Longitude")

        if not mmsi or lat is None or lon is None:
            return None
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return None

        spd = pos.get("Sog")          # Speed over ground (knots)
        hdg = pos.get("TrueHeading")  # 0–359, 511 = N/A
        cog = pos.get("Cog")

        return {
            "id":   mmsi,
            "name": meta.get("ShipName", "").strip() or None,
            "lat":  lat,
            "lon":  lon,
            "spd":  round(float(spd), 1) if spd else None,
            "hdg":  int(hdg) if hdg is not None and hdg != 511 else None,
            "dest": None,
            "ts":   int(time.time()),
            # Internal only — not sent to frontend
            "_cog":  cog,
            "_type": "ship",
        }
    except Exception as exc:
        log.debug("AIS parse error: %s", exc)
        return None


async def _cache_ship(ship: dict) -> None:
    """Write ship to Redis and persist to DB."""
    mmsi = ship["id"]
    try:
        wire = {k: v for k, v in ship.items() if not k.startswith("_")}
        await redis.hset("ships", mmsi, json.dumps(wire, separators=(",", ":")))
    except Exception as exc:
        log.error("Redis ship write error: %s", exc)

    try:
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            session.add(ShipPosition(
                time        = now,
                mmsi        = mmsi,
                name        = ship.get("name"),
                lat         = ship["lat"],
                lon         = ship["lon"],
                speed       = ship.get("spd"),
                heading     = ship.get("hdg"),
                course      = ship.get("_cog"),
                ship_type   = None,
                status      = None,
                destination = ship.get("dest"),
            ))
            await session.commit()
    except Exception as exc:
        log.error("DB ship write error: %s", exc)


async def run() -> None:
    """
    Persistent AIS relay loop with exponential back-off reconnect.
    Runs forever as a background task.
    """
    if not settings.AIS_KEY:
        log.warning("AIS_KEY not set — ship tracking disabled")
        return

    subscribe_msg = json.dumps({
        "APIKey":    settings.AIS_KEY,
        "BoundingBoxes": [[[-90, -180], [90, 180]]],  # global
    })

    backoff = 2  # seconds — doubles on each failed attempt (max 60s)

    while True:
        try:
            log.info("Connecting to aisstream.io …")
            async with websockets.connect(
                _AIS_URL,
                ping_interval=20,
                ping_timeout=30,
                close_timeout=5,
            ) as ws:
                await ws.send(subscribe_msg)
                backoff = 2  # reset on successful connect
                log.info("AIS stream connected ✓")

                async for raw in ws:
                    try:
                        ship = _parse_ais(json.loads(raw))
                        if ship is None:
                            continue

                        await _cache_ship(ship)

                        # Broadcast to WS clients
                        if manager.count > 0:
                            wire = {k: v for k, v in ship.items() if not k.startswith("_")}
                            await manager.broadcast({
                                "type":   "delta",
                                "ts":     ship["ts"],
                                "upsert": [wire],
                                "remove": [],
                            })
                    except Exception as exc:
                        log.debug("AIS message error: %s", exc)

        except Exception as exc:
            log.warning("AIS disconnected: %s — retrying in %ds", exc, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
