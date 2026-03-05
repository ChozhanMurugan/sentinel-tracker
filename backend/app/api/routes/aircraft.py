"""REST API routes for aircraft data."""
from __future__ import annotations
import json
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import select, text

from app.redis_client import redis
from app.database import AsyncSessionLocal
from app.models.aircraft import AircraftPosition

router = APIRouter(prefix="/api/aircraft", tags=["aircraft"])


@router.get("")
async def get_live_aircraft():
    """Return all currently tracked aircraft (from Redis hot cache)."""
    try:
        raw_values = await redis.hvals("aircraft")
        return [json.loads(v) for v in raw_values]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cache unavailable: {exc}")


@router.get("/{icao24}")
async def get_aircraft(icao24: str):
    """Return current state of a single aircraft."""
    raw = await redis.hget("aircraft", icao24.lower())
    if raw is None:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    return json.loads(raw)


@router.get("/{icao24}/history")
async def get_history(
    icao24:  str,
    hours:   float = Query(default=2.0, ge=0.1, le=168.0),
    limit:   int   = Query(default=500, ge=1, le=5000),
):
    """
    Return position history trail for an aircraft.
    TimescaleDB query — fast even with millions of rows thanks to hypertable index.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT time, lat, lon, altitude_m, heading
                    FROM aircraft_positions
                    WHERE icao24 = :icao
                      AND time > NOW() - INTERVAL ':hours hours'
                    ORDER BY time DESC
                    LIMIT :limit
                """),
                {"icao": icao24.lower(), "hours": hours, "limit": limit},
            )
            rows = result.fetchall()

        return [
            {"ts": int(r[0].timestamp()), "lat": r[1], "lon": r[2],
             "alt": r[3], "hdg": r[4]}
            for r in rows
        ]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/bbox/search")
async def get_aircraft_in_bbox(
    minlat: float = Query(..., ge=-90,  le=90),
    maxlat: float = Query(..., ge=-90,  le=90),
    minlon: float = Query(..., ge=-180, le=180),
    maxlon: float = Query(..., ge=-180, le=180),
):
    """Return all live aircraft within a geographic bounding box."""
    try:
        raw_values = await redis.hvals("aircraft")
        results = []
        for raw in raw_values:
            e = json.loads(raw)
            lat, lon = e.get("lat"), e.get("lon")
            if lat and lon and minlat <= lat <= maxlat and minlon <= lon <= maxlon:
                results.append(e)
        return results
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
