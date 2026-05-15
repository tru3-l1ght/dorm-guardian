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
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


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


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, index=True, nullable=True)
    method = Column(String, nullable=False)
    path = Column(String, index=True, nullable=False)
    status_code = Column(Integer, nullable=False)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, index=True, nullable=True)
    event_type = Column(String, index=True, nullable=False)
    severity = Column(String, nullable=False)
    method = Column(String, nullable=True)
    path = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    details = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())