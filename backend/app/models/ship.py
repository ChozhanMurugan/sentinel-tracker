"""SQLAlchemy ORM model — ship_positions (TimescaleDB hypertable)."""
from sqlalchemy import Column, String, Float, SmallInteger
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.database import Base


class ShipPosition(Base):
    __tablename__ = "ship_positions"

    time        = Column(TIMESTAMP(timezone=True), primary_key=True, nullable=False)
    mmsi        = Column(String(12), primary_key=True, nullable=False)
    name        = Column(String(64))
    lat         = Column(Float)
    lon         = Column(Float)
    speed       = Column(Float)
    heading     = Column(SmallInteger)
    course      = Column(SmallInteger)
    ship_type   = Column(SmallInteger)
    status      = Column(String(32))
    destination = Column(String(64))
