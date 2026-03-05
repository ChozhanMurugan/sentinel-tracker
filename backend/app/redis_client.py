"""
Async Redis client — single connection pool used app-wide.
"""
from redis.asyncio import from_url
from app.config import settings

redis = from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
)

# ── Redis key conventions ─────────────────────────────────────
# aircraft hash  → HSET "aircraft"  <icao24>  <json>
# ships hash     → HSET "ships"     <mmsi>    <json>
#
# get all aircraft:  await redis.hvals("aircraft")
# get one:           await redis.hget("aircraft", icao24)
# upsert:            await redis.hset("aircraft", icao24, json_str)
# delete:            await redis.hdel("aircraft", icao24)
