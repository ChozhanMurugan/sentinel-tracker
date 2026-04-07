"""
SENTINEL Backend — Configuration
Reads from .env file using pydantic-settings.
"""
from __future__ import annotations
import json
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://sentinel:sentinel_pass@localhost:5432/sentinel"
    )

    # ── Redis ─────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── Kafka ─────────────────────────────────────────────────
    KAFKA_BROKER: str = "localhost:9092"
    KAFKA_TOPIC_AIRCRAFT: str = "flight_states"

    # ── OpenSky ───────────────────────────────────────────────
    OPENSKY_USER: str = ""          # legacy basic auth
    OPENSKY_PASS: str = ""          # legacy basic auth
    OPENSKY_CLIENT_ID: str = ""     # OAuth2 client credentials
    OPENSKY_CLIENT_SECRET: str = "" # OAuth2 client credentials
    OPENSKY_REFRESH_S: int = 10

    # ── AIS ───────────────────────────────────────────────────
    AIS_KEY: str = ""

    # ── Server ───────────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # Seconds before an aircraft with no new data is pruned
    STALE_THRESHOLD_S: int = 90

    # CORS origins (stored as JSON array string in .env)
    CORS_ORIGINS: str = (
        '["http://localhost:8787","http://127.0.0.1:5500"]'
    )

    @property
    def cors_list(self) -> list[str]:
        try:
            return json.loads(self.CORS_ORIGINS)
        except Exception:
            return ["*"]


settings = Settings()
