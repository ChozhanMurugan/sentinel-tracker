"""Pydantic schemas for ship responses."""
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class ShipOut(BaseModel):
    """Compact wire format for ships."""
    id:   str              # mmsi
    name: Optional[str]
    lat:  float
    lon:  float
    spd:  Optional[float]
    hdg:  Optional[int]
    dest: Optional[str]    # destination
    ts:   int
