"""
Data collector — polls OpenSky and maintains a per-aircraft position buffer.
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

import msgpack
from aiokafka import AIOKafkaConsumer

from .config import settings


@dataclass
class Snapshot:
    """One position fix for an aircraft."""
    ts: float          # epoch seconds
    icao24: str
    callsign: str
    lat: float
    lon: float
    altitude: float    # metres (baro)
    speed: float       # m/s ground speed
    heading: float     # degrees
    vert_rate: float   # m/s
    on_ground: bool
    country: str
    squawk: str


@dataclass
class Collector:
    """Polls OpenSky and keeps a sliding window of snapshots per aircraft."""

    _buffer: dict[str, deque[Snapshot]] = field(default_factory=lambda: defaultdict(lambda: deque(maxlen=settings.buffer_depth)))
    _latest: dict[str, Snapshot] = field(default_factory=dict)
    _running: bool = False
    _total_msgs: int = 0
    _last_msg_ts: float = 0
    _aircraft_seen: int = 0

    # ── public ---------------------------------------------------------

    def get_buffer(self) -> dict[str, deque[Snapshot]]:
        return self._buffer

    def get_latest(self) -> dict[str, Snapshot]:
        return self._latest

    @property
    def stats(self) -> dict:
        return {
            "total_kafka_msgs": self._total_msgs,
            "last_msg_ts": self._last_msg_ts,
            "aircraft_tracked": len(self._latest),
            "buffer_entries": sum(len(v) for v in self._buffer.values()),
        }

    # ── lifecycle ------------------------------------------------------

    async def start(self):
        self._running = True

        while self._running:
            consumer: AIOKafkaConsumer | None = None
            try:
                consumer = AIOKafkaConsumer(
                    settings.kafka_topic,
                    bootstrap_servers=settings.kafka_broker,
                    value_deserializer=lambda m: msgpack.unpackb(m),
                    client_id="sentinel-ml-collector",
                    group_id="sentinel-ml-group",
                )
                await consumer.start()
                print(f"[Collector] Connected to Kafka broker at {settings.kafka_broker}")

                while self._running:
                    msg = await consumer.getone()
                    # msg.value contains the delta payload published by backend worker
                    self._process_msg(msg.value)

            except asyncio.CancelledError:
                break  # lifespan shutdown — exit cleanly
            except Exception as e:
                print(f"[Collector] Consumer error: {e} — retrying in 10s")
                await asyncio.sleep(10)
            finally:
                if consumer is not None:
                    try:
                        await consumer.stop()
                    except Exception:
                        pass

    def stop(self):
        self._running = False

    # ── internal -------------------------------------------------------

    def _process_msg(self, data: dict):
        upserts = data.get("upsert", [])
        if not upserts:
            return

        now = time.time()
        self._total_msgs += 1
        self._last_msg_ts = now
        seen = 0

        for state in upserts:
            icao24 = state.get("id")
            if not icao24:
                continue
                
            snap = Snapshot(
                ts=state.get("ts", now),
                icao24=icao24,
                callsign=(state.get("cs") or "").strip(),
                lat=state.get("lat") or 0.0,
                lon=state.get("lon") or 0.0,
                altitude=state.get("alt") or 0.0,
                # Backend publishes speed in knots; features.py expects m/s
                speed=(state.get("spd") or 0.0) / 1.944,
                heading=state.get("hdg") or 0.0,
                vert_rate=state.get("vrt") or 0.0,
                on_ground=state.get("gnd", False),
                country=state.get("cty", ""),
                squawk=state.get("sq", ""),
            )
            self._buffer[icao24].append(snap)
            self._latest[icao24] = snap
            seen += 1

        self._aircraft_seen = seen
        # print(f"[Collector] msg #{self._total_msgs} processed: {seen} aircraft updated")

