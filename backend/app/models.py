from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from sqlalchemy.sql import func

from app.database import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True, nullable=False)

    temperature_c = Column(Float, nullable=False)
    humidity_percent = Column(Float, nullable=False)
    air_quality = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FanState(Base):
    __tablename__ = "fan_state"

    id = Column(Integer, primary_key=True, index=True)
    is_on = Column(Boolean, default=False, nullable=False)
    mode = Column(String, default="auto", nullable=False)
    reason = Column(String, default="Initial state", nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())