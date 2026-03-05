"""
WebSocket endpoint — /ws
On connect: send full snapshot from Redis.
Ongoing: receive delta broadcasts from OpenSky poller and AIS relay.
"""
from __future__ import annotations
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.redis_client import redis
from app.services.broadcaster import manager

log = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)

    try:
        # ── Send initial snapshot from Redis ──────────────────
        aircraft_raw = await redis.hvals("aircraft")
        ships_raw    = await redis.hvals("ships")

        snapshot = {
            "type":     "snapshot",
            "ts":       int(time.time()),
            "aircraft": [json.loads(r) for r in aircraft_raw],
            "ships":    [json.loads(r) for r in ships_raw],
        }
        await manager.send_to(ws, snapshot)
        log.info(
            "Sent snapshot: %d aircraft, %d ships",
            len(aircraft_raw), len(ships_raw)
        )

        # ── Keep connection alive, wait for disconnect ─────────
        # (all updates are pushed by the broadcaster, not this loop)
        while True:
            try:
                # Receive heartbeat/ping from client (ignore content)
                await ws.receive_text()
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.warning("WS error: %s", exc)
    finally:
        manager.disconnect(ws)
