"""
Data collector — polls OpenSky and maintains a per-aircraft position buffer.
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

import httpx

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
    _total_polls: int = 0
    _last_poll_ts: float = 0
    _aircraft_seen: int = 0

    # ── public ---------------------------------------------------------

    def get_buffer(self) -> dict[str, deque[Snapshot]]:
        return self._buffer

    def get_latest(self) -> dict[str, Snapshot]:
        return self._latest

    @property
    def stats(self) -> dict:
        return {
            "total_polls": self._total_polls,
            "last_poll_ts": self._last_poll_ts,
            "aircraft_tracked": len(self._latest),
            "buffer_entries": sum(len(v) for v in self._buffer.values()),
        }

    # ── lifecycle ------------------------------------------------------

    async def start(self):
        self._running = True
        while self._running:
            await self._poll()
            await asyncio.sleep(settings.poll_interval_s)

    def stop(self):
        self._running = False

    # ── internal -------------------------------------------------------

    async def _poll(self):
        try:
            async with httpx.AsyncClient(timeout=15, verify=False) as client:
                resp = await client.get(settings.opensky_url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            print(f"[Collector] poll error: {exc}")
            return

        states = data.get("states") or []
        now = time.time()
        self._total_polls += 1
        self._last_poll_ts = now
        seen = 0

        for s in states:
            if s[6] is None or s[5] is None:
                continue  # no position

            icao24 = s[0]
            snap = Snapshot(
                ts=s[3] or now,
                icao24=icao24,
                callsign=(s[1] or "").strip(),
                lat=s[6],
                lon=s[5],
                altitude=s[7] or 0,       # baro altitude metres
                speed=s[9] or 0,           # ground speed m/s
                heading=s[10] or 0,
                vert_rate=s[11] or 0,
                on_ground=bool(s[8]),
                country=s[2] or "",
                squawk=s[14] or "",
            )
            self._buffer[icao24].append(snap)
            self._latest[icao24] = snap
            seen += 1

        self._aircraft_seen = seen
        print(f"[Collector] poll #{self._total_polls}: {seen} aircraft")
