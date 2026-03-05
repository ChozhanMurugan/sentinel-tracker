"""Pydantic schemas for WebSocket messages."""
from __future__ import annotations
from typing import Literal, Union
from pydantic import BaseModel
from app.schemas.aircraft import AircraftOut
from app.schemas.ship import ShipOut


class SnapshotMessage(BaseModel):
    """Full state — sent once when a client first connects."""
    type:     Literal["snapshot"] = "snapshot"
    ts:       int
    aircraft: list[AircraftOut]
    ships:    list[ShipOut]


class DeltaMessage(BaseModel):
    """Only what changed — sent every refresh cycle."""
    type:   Literal["delta"] = "delta"
    ts:     int
    upsert: list[Union[AircraftOut, ShipOut]]  # new or updated
    remove: list[str]                          # stale entity IDs


class StatsMessage(BaseModel):
    """Live contact counts — sent every 30 seconds."""
    type:       Literal["stats"] = "stats"
    commercial: int
    military:   int
    ships:      int
    total:      int
