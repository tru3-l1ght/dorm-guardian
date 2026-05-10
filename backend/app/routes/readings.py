from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SensorReading
from app.schemas import SensorReadingOut

router = APIRouter(prefix="/api/readings", tags=["readings"])


@router.get("/latest", response_model=SensorReadingOut | None)
def get_latest_reading(db: Session = Depends(get_db)):
    return (
        db.query(SensorReading)
        .order_by(SensorReading.created_at.desc())
        .first()
    )


@router.get("/history", response_model=list[SensorReadingOut])
def get_reading_history(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    readings = (
        db.query(SensorReading)
        .order_by(SensorReading.created_at.desc())
        .limit(limit)
        .all()
    )

    return list(reversed(readings))