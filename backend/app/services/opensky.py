"""
OpenSky Network polling service.
Fetches all aircraft states every OPENSKY_REFRESH_S seconds,
classifies military, persists to TimescaleDB, updates Redis, broadcasts delta.

OpenSky state vector fields (by index):
  0  icao24       6  latitude      12 sensors
  1  callsign     7  baro_altitude 13 geo_altitude
  2  origin_cty   8  on_ground     14 squawk
  3  time_pos     9  velocity(m/s) 15 spi
  4  last_contact 10 true_track    16 position_source
  5  longitude    11 vertical_rate
"""
from __future__ import annotations
import asyncio
import json
import logging
import time
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.redis_client import redis
from app.services.military import classify
from app.services.broadcaster import manager
from app.database import AsyncSessionLocal
from app.models.aircraft import AircraftPosition
from app.services.kafka_publisher import publish_states

log = logging.getLogger(__name__)

# OpenSky base URL
_URL = "https://opensky-network.org/api/states/all"
_TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

# Token cache
_token: str | None = None
_token_expiry: float = 0.0

# In-memory snapshot of previous cycle for delta calculation
_prev_snapshot: dict[str, dict] = {}


async def _get_token() -> str | None:
    """Fetch (or return cached) OAuth2 Bearer token from OpenSky."""
    global _token, _token_expiry
    if not (settings.OPENSKY_CLIENT_ID and settings.OPENSKY_CLIENT_SECRET):
        return None
    if _token and time.time() < _token_expiry - 30:
        return _token
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _TOKEN_URL,
                data={
                    "grant_type":    "client_credentials",
                    "client_id":     settings.OPENSKY_CLIENT_ID,
                    "client_secret": settings.OPENSKY_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code == 200:
            body = resp.json()
            _token = body["access_token"]
            _token_expiry = time.time() + body.get("expires_in", 3600)
            log.info("OpenSky OAuth2 token acquired (expires in %ds)", body.get("expires_in", 3600))
            return _token
        else:
            log.error("OpenSky token fetch failed: HTTP %d — %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        log.error("OpenSky token error: %s", exc)
    return None


def _parse_state(state: list) -> dict | None:
    """Parse a single OpenSky state vector into a clean dict."""
    try:
        icao24 = (state[0] or "").strip().lower()
        lat    = state[6]
        lon    = state[5]

        # Skip if no position
        if lat is None or lon is None or not icao24:
            return None
        # Skip implausible coordinates
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return None

        callsign  = (state[1] or "").strip() or None
        alt       = state[7]                      # baro altitude (m)
        on_ground = bool(state[8])
        speed_ms  = state[9]                      # velocity in m/s
        speed_kts = round(speed_ms * 1.944, 1) if speed_ms else None
        heading   = state[10]
        vert_rate = state[11]
        squawk    = state[14]
        country   = state[2]
        ts        = int(state[3] or state[4] or time.time())

        return {
            "id":  icao24,
            "cs":  callsign,
            "lat": lat,
            "lon": lon,
            "alt": round(alt, 1) if alt else None,
            "spd": speed_kts,
            "hdg": int(heading) if heading is not None else None,
            "vrt": round(vert_rate, 2) if vert_rate else None,
            "sq":  squawk,
            "cty": country,
            "mil": classify(icao24, callsign),
            "gnd": on_ground,
            "ts":  ts,
        }
    except Exception as exc:
        log.debug("State parse error: %s", exc)
        return None


async def _fetch_opensky() -> list[dict]:
    """Fetch all states from OpenSky. Prefers OAuth2; falls back to Basic Auth."""
    try:
        headers = {}
        auth = None

        # Prefer OAuth2 client credentials
        token = await _get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif settings.OPENSKY_USER and settings.OPENSKY_PASS:
            auth = (settings.OPENSKY_USER, settings.OPENSKY_PASS)

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_URL, auth=auth, headers=headers)

        if resp.status_code == 401:
            # Token may have expired — clear cache and retry once
            global _token, _token_expiry
            _token, _token_expiry = None, 0.0
            log.warning("OpenSky 401 — clearing token cache, will retry next cycle")
            return []

        if resp.status_code == 429:
            log.warning("OpenSky rate limited (429) — backing off 60s")
            await asyncio.sleep(60)
            return []

        if resp.status_code != 200:
            log.warning("OpenSky HTTP %d", resp.status_code)
            return []

        data = resp.json()
        states = data.get("states") or []
        parsed = [e for s in states if (e := _parse_state(s))]
        log.info("OpenSky: fetched %d aircraft", len(parsed))
        return parsed

    except httpx.TimeoutException:
        log.warning("OpenSky request timed out")
        return []
    except Exception as exc:
        log.error("OpenSky fetch error: %s", exc)
        return []


async def _persist(entities: list[dict]) -> None:
    """Bulk-insert aircraft positions into TimescaleDB."""
    if not entities:
        return
    try:
        now = datetime.now(timezone.utc)
        rows = [
            AircraftPosition(
                time       = now,
                icao24     = e["id"],
                callsign   = e["cs"],
                lat        = e["lat"],
                lon        = e["lon"],
                altitude_m = e["alt"],
                speed_kts  = e["spd"],
                heading    = e["hdg"],
                vert_rate  = e["vrt"],
                squawk     = e["sq"],
                country    = e["cty"],
                military   = e["mil"],
                on_ground  = e["gnd"],
            )
            for e in entities
        ]
        async with AsyncSessionLocal() as session:
            session.add_all(rows)
            await session.commit()
    except Exception as exc:
        log.error("DB persist error: %s", exc)


async def _update_redis(entities: list[dict]) -> set[str]:
    """
    Cache latest state for all entities in Redis.
    Returns set of IDs that changed or are new (for delta).
    """
    changed: set[str] = set()
    if not entities:
        return changed
    try:
        pipe = redis.pipeline()
        for e in entities:
            icao24 = e["id"]
            pipe.hset("aircraft", icao24, json.dumps(e, separators=(",", ":")))
            changed.add(icao24)
        await pipe.execute()
    except Exception as exc:
        log.error("Redis update error: %s", exc)
    return changed


async def _prune_stale() -> list[str]:
    """Remove aircraft not seen for STALE_THRESHOLD_S from Redis."""
    removed: list[str] = []
    try:
        now = time.time()
        all_raw = await redis.hgetall("aircraft")
        pipe = redis.pipeline()
        for icao24, raw in all_raw.items():
            try:
                data = json.loads(raw)
                if now - data.get("ts", 0) > settings.STALE_THRESHOLD_S:
                    pipe.hdel("aircraft", icao24)
                    removed.append(icao24)
            except Exception:
                pass
        if removed:
            await pipe.execute()
            log.debug("Pruned %d stale aircraft", len(removed))
    except Exception as exc:
        log.error("Stale prune error: %s", exc)
    return removed


async def poll() -> None:
    """One full poll cycle — fetch, persist, cache, broadcast."""
    entities = await _fetch_opensky()
    if not entities:
        return

    # Run DB persist, Redis update, and Kafka publish in parallel
    changed, _, _ = await asyncio.gather(
        _update_redis(entities),
        _persist(entities),
        publish_states(entities),
    )
    removed = await _prune_stale()

    # Broadcast delta to all WS clients
    if manager.count > 0:
        ts = int(time.time())
        await manager.broadcast({
            "type":   "delta",
            "ts":     ts,
            "upsert": entities,
            "remove": removed,
        })
