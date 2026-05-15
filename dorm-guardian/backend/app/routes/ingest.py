from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.alert_logic import create_alert_with_cooldown
from app.database import get_db
from app.fan_logic import decide_fan_state
from app.models import SensorReading, FanState
from app.schemas import SensorReadingCreate, SensorReadingOut

router = APIRouter(prefix="/api/device-ingest", tags=["device-ingest"])


@router.post("/sensor-reading", response_model=SensorReadingOut)
def ingest_sensor_reading(
    payload: SensorReadingCreate,
    db: Session = Depends(get_db),
):
    reading = SensorReading(
        device_id=payload.device_id,
        temperature_c=payload.temperature_c,
        humidity_percent=payload.humidity_percent,
        air_quality=payload.air_quality,
    )

    db.add(reading)

    fan_state = db.query(FanState).first()

    if fan_state is None:
        fan_state = FanState(
            is_on=False,
            mode="auto",
            reason="Initial state",
        )
        db.add(fan_state)
        db.flush()

    previous_fan_state = fan_state.is_on

    new_state, reason = decide_fan_state(
        temperature_c=payload.temperature_c,
        current_state=fan_state.is_on,
        automation_enabled=True,
    )

    fan_state.is_on = new_state
    fan_state.reason = reason

    if new_state != previous_fan_state:
        create_alert_with_cooldown(
            db=db,
            alert_type="device.fan_state_changed",
            severity="info",
            title="Fan state changed",
            message=f"Fan turned {'ON' if new_state else 'OFF'}: {reason}",
            cooldown_minutes=1,
        )

    if payload.temperature_c >= 30.0:
        create_alert_with_cooldown(
            db=db,
            alert_type="environment.temperature_high",
            severity="warning",
            title="High temperature detected",
            message=f"Temperature reached {payload.temperature_c:.1f}°C",
            cooldown_minutes=5,
        )

    if payload.air_quality >= 1800:
        create_alert_with_cooldown(
            db=db,
            alert_type="environment.air_quality_bad",
            severity="warning",
            title="Poor air quality detected",
            message=f"Air quality reading reached {payload.air_quality:.0f}",
            cooldown_minutes=5,
        )

    db.commit()
    db.refresh(reading)

    return reading