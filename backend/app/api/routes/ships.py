"""REST API routes for ship data."""
from __future__ import annotations
import json
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.redis_client import redis
from app.database import AsyncSessionLocal

router = APIRouter(prefix="/api/ships", tags=["ships"])


@router.get("")
async def get_live_ships():
    """All currently tracked ships from Redis."""
    try:
        raw_values = await redis.hvals("ships")
        return [json.loads(v) for v in raw_values]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/{mmsi}")
async def get_ship(mmsi: str):
    raw = await redis.hget("ships", mmsi)
    if raw is None:
        raise HTTPException(status_code=404, detail="Ship not found")
    return json.loads(raw)


@router.get("/{mmsi}/history")
async def get_ship_history(mmsi: str, hours: float = 6.0):
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT time, lat, lon, speed, heading
                    FROM ship_positions
                    WHERE mmsi = :mmsi
                      AND time > NOW() - INTERVAL ':hours hours'
                    ORDER BY time DESC LIMIT 500
                """),
                {"mmsi": mmsi, "hours": hours},
            )
        return [
            {"ts": int(r[0].timestamp()), "lat": r[1], "lon": r[2],
             "spd": r[3], "hdg": r[4]}
            for r in result.fetchall()
        ]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
