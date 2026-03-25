"""
Tests for anomaly detection.
"""
from collections import deque

import numpy as np

from app.anomaly import AnomalyDetector
from app.collector import Snapshot
from app.features import AircraftFeatures, extract_features


def _snap(ts=0, icao="test", lat=51.5, lon=-0.1, alt=10000,
          speed=250, heading=90, vert=0, ground=False):
    return Snapshot(
        ts=ts, icao24=icao, callsign="TST123",
        lat=lat, lon=lon, altitude=alt, speed=speed,
        heading=heading, vert_rate=vert, on_ground=ground,
        country="UK", squawk="1000",
    )


def _make_normal_features(n=500) -> list[AircraftFeatures]:
    """Create N 'normal' cruise features."""
    rng = np.random.RandomState(42)
    results = []
    for i in range(n):
        results.append(AircraftFeatures(
            icao24=f"ac{i:04d}",
            speed=250 + rng.normal(0, 10),
            altitude=10000 + rng.normal(0, 500),
            vert_rate=rng.normal(0, 1),
            heading_delta=rng.normal(0, 3),
            turn_rate=rng.normal(0, 5),
            speed_variance=rng.uniform(0, 5),
            altitude_variance=rng.uniform(0, 200),
            is_circling=False,
            distance_moved=rng.uniform(5, 15),
            ground_ratio=0.0,
        ))
    return results


class TestAnomalyDetector:
    def test_not_trained_returns_empty(self):
        det = AnomalyDetector()
        feat = [AircraftFeatures(
            icao24="x", speed=0, altitude=0, vert_rate=0,
            heading_delta=0, turn_rate=0, speed_variance=0,
            altitude_variance=0, is_circling=False,
            distance_moved=0, ground_ratio=0,
        )]
        results = det.score(feat)
        assert results == []
        assert det.is_trained is False

    def test_fit_with_enough_samples(self):
        det = AnomalyDetector()
        normals = _make_normal_features(500)
        fitted = det.maybe_fit(normals)
        assert fitted is True
        assert det.is_trained is True

    def test_fit_rejected_with_too_few(self):
        det = AnomalyDetector()
        few = _make_normal_features(10)
        fitted = det.maybe_fit(few)
        assert fitted is False

    def test_normal_aircraft_not_flagged(self):
        det = AnomalyDetector()
        normals = _make_normal_features(500)
        det.maybe_fit(normals)

        # Score a normal aircraft
        test = [AircraftFeatures(
            icao24="normal", speed=250, altitude=10000, vert_rate=0,
            heading_delta=2, turn_rate=3, speed_variance=3,
            altitude_variance=100, is_circling=False,
            distance_moved=10, ground_ratio=0,
        )]
        results = det.score(test)
        assert len(results) == 1
        assert results[0].is_anomaly == False

    def test_obvious_anomaly_flagged(self):
        det = AnomalyDetector()
        normals = _make_normal_features(500)
        det.maybe_fit(normals)

        # Score a clearly anomalous aircraft (hovering at 0 speed, circling)
        test = [AircraftFeatures(
            icao24="anomalous", speed=0, altitude=500, vert_rate=-30,
            heading_delta=90, turn_rate=500, speed_variance=100,
            altitude_variance=5000, is_circling=True,
            distance_moved=0.1, ground_ratio=0,
        )]
        results = det.score(test)
        assert len(results) == 1
        assert results[0].is_anomaly == True
        assert len(results[0].reasons) > 0

    def test_stats(self):
        det = AnomalyDetector()
        stats = det.stats
        assert stats["trained"] is False
        assert stats["sample_count"] == 0
