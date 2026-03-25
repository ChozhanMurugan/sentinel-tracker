"""
Feature engineering — extracts ML feature vectors from the position buffer.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections import deque
    from .collector import Snapshot


@dataclass
class AircraftFeatures:
    """Computed features for one aircraft."""
    icao24: str
    speed: float
    altitude: float
    vert_rate: float
    heading_delta: float       # deg change between last two snapshots
    turn_rate: float           # avg deg/min across buffer
    speed_variance: float
    altitude_variance: float
    is_circling: bool          # cumulative heading > 300° over buffer
    distance_moved: float      # km across buffer
    ground_ratio: float        # fraction of snapshots on_ground

    def to_vector(self) -> np.ndarray:
        return np.array([
            self.speed,
            self.altitude,
            self.vert_rate,
            self.heading_delta,
            self.turn_rate,
            self.speed_variance,
            self.altitude_variance,
            float(self.is_circling),
            self.distance_moved,
            self.ground_ratio,
        ], dtype=np.float64)

    @staticmethod
    def feature_names() -> list[str]:
        return [
            "speed", "altitude", "vert_rate", "heading_delta",
            "turn_rate", "speed_variance", "altitude_variance",
            "is_circling", "distance_moved", "ground_ratio",
        ]


# ── helpers ──────────────────────────────────────────────────────

def _heading_diff(a: float, b: float) -> float:
    """Signed heading difference in [-180, 180]."""
    d = (b - a) % 360
    return d if d <= 180 else d - 360


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── main entry point ─────────────────────────────────────────────

def extract_features(icao24: str, history: deque[Snapshot]) -> AircraftFeatures | None:
    """Compute feature vector from a position buffer.  Returns None if < 2 snapshots."""
    if len(history) < 2:
        return None

    snaps = list(history)
    latest = snaps[-1]

    # heading deltas
    heading_deltas = [abs(_heading_diff(snaps[i].heading, snaps[i + 1].heading)) for i in range(len(snaps) - 1)]
    cumulative_heading = sum(heading_deltas)

    # time span
    dt = max(snaps[-1].ts - snaps[0].ts, 1.0)  # seconds
    turn_rate = (cumulative_heading / dt) * 60   # deg/min

    # speed / altitude arrays
    speeds = [s.speed for s in snaps]
    alts = [s.altitude for s in snaps]

    # distance
    total_dist = sum(
        _haversine_km(snaps[i].lat, snaps[i].lon, snaps[i + 1].lat, snaps[i + 1].lon)
        for i in range(len(snaps) - 1)
    )

    # ground ratio
    ground_count = sum(1 for s in snaps if s.on_ground)

    return AircraftFeatures(
        icao24=icao24,
        speed=latest.speed,
        altitude=latest.altitude,
        vert_rate=latest.vert_rate,
        heading_delta=heading_deltas[-1] if heading_deltas else 0.0,
        turn_rate=turn_rate,
        speed_variance=float(np.std(speeds)),
        altitude_variance=float(np.std(alts)),
        is_circling=cumulative_heading > 300,
        distance_moved=total_dist,
        ground_ratio=ground_count / len(snaps),
    )


def extract_all(buffer: dict[str, deque[Snapshot]]) -> list[AircraftFeatures]:
    """Extract features for every aircraft with enough history."""
    results = []
    for icao24, history in buffer.items():
        feat = extract_features(icao24, history)
        if feat is not None:
            results.append(feat)
    return results
