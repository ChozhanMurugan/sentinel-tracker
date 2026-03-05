"""SQLAlchemy ORM model — aircraft_positions (TimescaleDB hypertable)."""
from sqlalchemy import Column, String, Float, Boolean, SmallInteger
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.database import Base


class AircraftPosition(Base):
    __tablename__ = "aircraft_positions"

    # TimescaleDB hypertable partition key
    time        = Column(TIMESTAMP(timezone=True), primary_key=True, nullable=False)
    icao24      = Column(String(8),   primary_key=True, nullable=False)
    callsign    = Column(String(16))
    lat         = Column(Float)
    lon         = Column(Float)
    altitude_m  = Column(Float)
    speed_kts   = Column(Float)
    heading     = Column(SmallInteger)
    vert_rate   = Column(Float)
    squawk      = Column(String(8))
    country     = Column(String(64))
    military    = Column(Boolean, default=False)
    on_ground   = Column(Boolean, default=False)
