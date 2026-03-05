"""Pydantic schemas for aircraft responses."""
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class AircraftOut(BaseModel):
    """Compact wire format sent to frontend clients."""
    id:  str              # icao24
    cs:  Optional[str]    # callsign
    lat: float
    lon: float
    alt: Optional[float]  # altitude_m
    spd: Optional[float]  # speed_kts
    hdg: Optional[int]    # heading degrees
    vrt: Optional[float]  # vertical rate m/s
    sq:  Optional[str]    # squawk
    cty: Optional[str]    # country
    mil: bool             # military flag
    gnd: bool             # on_ground flag
    ts:  int              # unix timestamp (seconds)


class AircraftHistoryPoint(BaseModel):
    """Single position in an aircraft's history trail."""
    ts:  int
    lat: float
    lon: float
    alt: Optional[float]
    hdg: Optional[int]
