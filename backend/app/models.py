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


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String, index=True, nullable=False)
    severity = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)