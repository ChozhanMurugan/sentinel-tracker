"""
SENTINEL-ML configuration.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenSky
    opensky_url: str = "https://opensky-network.org/api/states/all"
    poll_interval_s: int = 10

    # Anomaly detector
    anomaly_contamination: float = 0.02   # expect ~2 % of aircraft are anomalous
    min_samples_to_train: int = 300       # train after this many aircraft seen
    refit_interval_s: int = 300           # re-train every 5 min
    buffer_depth: int = 6                 # keep last N snapshots per aircraft

    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    cors_origins: list[str] = [
        "http://localhost:8787",
        "http://127.0.0.1:8787",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]

    model_config = {"env_prefix": "SENTINEL_ML_"}


settings = Settings()
