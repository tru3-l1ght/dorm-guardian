from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SensorReading
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
    db.commit()
    db.refresh(reading)

    return reading