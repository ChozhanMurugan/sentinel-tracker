"""
Tests for feature extraction.
"""
import math
from collections import deque

from app.collector import Snapshot
from app.features import extract_features, extract_all, _heading_diff, _haversine_km


def _snap(ts=0, icao="test", lat=51.5, lon=-0.1, alt=10000,
          speed=250, heading=90, vert=0, ground=False):
    return Snapshot(
        ts=ts, icao24=icao, callsign="TST123",
        lat=lat, lon=lon, altitude=alt, speed=speed,
        heading=heading, vert_rate=vert, on_ground=ground,
        country="UK", squawk="1000",
    )


class TestHeadingDiff:
    def test_simple(self):
        assert _heading_diff(10, 20) == 10

    def test_wrap_positive(self):
        assert _heading_diff(350, 10) == 20

    def test_wrap_negative(self):
        d = _heading_diff(10, 350)
        assert d == -20

    def test_same(self):
        assert _heading_diff(180, 180) == 0


class TestHaversine:
    def test_same_point(self):
        assert _haversine_km(51.5, -0.1, 51.5, -0.1) == 0.0

    def test_known_distance(self):
        # London to Paris ~ 340 km
        d = _haversine_km(51.5, -0.1, 48.86, 2.35)
        assert 330 < d < 360


class TestExtractFeatures:
    def test_too_few_snapshots(self):
        buf = deque([_snap(ts=0)])
        assert extract_features("test", buf) is None

    def test_basic_extraction(self):
        buf = deque([
            _snap(ts=0, heading=90),
            _snap(ts=10, heading=100),
            _snap(ts=20, heading=110),
        ])
        feat = extract_features("test", buf)
        assert feat is not None
        assert feat.icao24 == "test"
        assert feat.speed == 250
        assert feat.altitude == 10000
        assert feat.heading_delta == 10.0
        assert feat.is_circling is False
        assert feat.ground_ratio == 0.0

    def test_circling_detection(self):
        """Cumulative heading change > 300° should flag circling."""
        buf = deque([
            _snap(ts=0, heading=0),
            _snap(ts=10, heading=90),
            _snap(ts=20, heading=180),
            _snap(ts=30, heading=270),
            _snap(ts=40, heading=350),
        ])
        feat = extract_features("circ", buf)
        assert feat is not None
        assert feat.is_circling is True

    def test_on_ground_ratio(self):
        buf = deque([
            _snap(ts=0, ground=True),
            _snap(ts=10, ground=True),
            _snap(ts=20, ground=False),
            _snap(ts=30, ground=False),
        ])
        feat = extract_features("gnd", buf)
        assert feat is not None
        assert feat.ground_ratio == 0.5

    def test_feature_vector_shape(self):
        buf = deque([_snap(ts=0), _snap(ts=10)])
        feat = extract_features("vec", buf)
        assert feat is not None
        vec = feat.to_vector()
        assert len(vec) == 10
        assert len(feat.feature_names()) == 10


class TestExtractAll:
    def test_empty_buffer(self):
        assert extract_all({}) == []

    def test_skips_insufficient(self):
        buf = {"a": deque([_snap()])}
        assert extract_all(buf) == []

    def test_extracts_valid(self):
        buf = {
            "a": deque([_snap(ts=0), _snap(ts=10)]),
            "b": deque([_snap(ts=0)]),  # too few
        }
        results = extract_all(buf)
        assert len(results) == 1
        assert results[0].icao24 == "a"
