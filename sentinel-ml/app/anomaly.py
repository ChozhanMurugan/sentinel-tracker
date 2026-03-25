"""
Anomaly detection using Isolation Forest.
Self-trains on live data — no pre-trained model files needed.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import IsolationForest

from .config import settings
from .features import AircraftFeatures


@dataclass
class AnomalyResult:
    icao24: str
    score: float          # lower = more anomalous (sklearn convention: negative = outlier)
    is_anomaly: bool
    reasons: list[str]


@dataclass
class AnomalyDetector:
    _model: IsolationForest | None = None
    _trained: bool = False
    _last_fit_ts: float = 0
    _sample_count: int = 0
    _feature_means: np.ndarray | None = None
    _feature_stds: np.ndarray | None = None
    _anomaly_count: int = 0

    @property
    def is_trained(self) -> bool:
        return self._trained

    @property
    def stats(self) -> dict:
        return {
            "trained": self._trained,
            "sample_count": self._sample_count,
            "last_fit_ts": self._last_fit_ts,
            "anomaly_count": self._anomaly_count,
        }

    # ── train / re-fit ─────────────────────────────────────────

    def maybe_fit(self, features: list[AircraftFeatures]) -> bool:
        """Train or re-train if enough samples and enough time has passed."""
        now = time.time()

        if len(features) < settings.min_samples_to_train:
            return False

        if self._trained and (now - self._last_fit_ts) < settings.refit_interval_s:
            return False

        X = np.array([f.to_vector() for f in features])

        # replace NaN / Inf
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        # store normalization stats for reason generation
        self._feature_means = X.mean(axis=0)
        self._feature_stds = X.std(axis=0) + 1e-8

        self._model = IsolationForest(
            contamination=settings.anomaly_contamination,
            n_estimators=100,
            random_state=42,
            n_jobs=-1,
        )
        self._model.fit(X)
        self._trained = True
        self._last_fit_ts = now
        self._sample_count = len(X)
        print(f"[Anomaly] model fitted on {len(X)} samples")
        return True

    # ── predict ────────────────────────────────────────────────

    def score(self, features: list[AircraftFeatures]) -> list[AnomalyResult]:
        """Score a batch of aircraft.  Returns empty list if model not trained."""
        if not self._trained or self._model is None:
            return []

        X = np.array([f.to_vector() for f in features])
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        raw_scores = self._model.decision_function(X)   # higher = more normal
        predictions = self._model.predict(X)             # 1 = normal, -1 = anomaly

        results: list[AnomalyResult] = []
        anomaly_count = 0

        for i, feat in enumerate(features):
            is_anom = predictions[i] == -1
            if is_anom:
                anomaly_count += 1
            reasons = self._explain(feat, X[i]) if is_anom else []
            results.append(AnomalyResult(
                icao24=feat.icao24,
                score=float(raw_scores[i]),
                is_anomaly=is_anom,
                reasons=reasons,
            ))

        self._anomaly_count = anomaly_count
        return results

    # ── explanation ────────────────────────────────────────────

    def _explain(self, feat: AircraftFeatures, x: np.ndarray) -> list[str]:
        """Generate human-readable reasons for why this aircraft is anomalous."""
        if self._feature_means is None or self._feature_stds is None:
            return ["unusual flight pattern"]

        z_scores = (x - self._feature_means) / self._feature_stds
        names = AircraftFeatures.feature_names()
        reasons: list[str] = []

        REASON_MAP = {
            "speed": ("unusually slow", "unusually fast"),
            "altitude": ("unusually low altitude", "unusually high altitude"),
            "vert_rate": ("steep descent", "steep climb"),
            "heading_delta": ("steady course", "sharp heading change"),
            "turn_rate": ("low turn rate", "high turn rate — possible orbit"),
            "speed_variance": ("constant speed", "erratic speed changes"),
            "altitude_variance": ("stable altitude", "erratic altitude changes"),
            "is_circling": ("not circling", "circling / orbit pattern detected"),
            "distance_moved": ("stationary", "high distance covered"),
            "ground_ratio": ("airborne", "mostly on ground"),
        }

        for i, name in enumerate(names):
            if abs(z_scores[i]) > 2.0 and name in REASON_MAP:
                low_label, high_label = REASON_MAP[name]
                reasons.append(high_label if z_scores[i] > 0 else low_label)

        if feat.is_circling:
            if "circling / orbit pattern detected" not in reasons:
                reasons.append("circling / orbit pattern detected")

        return reasons if reasons else ["unusual flight pattern"]
