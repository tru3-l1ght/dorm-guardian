from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FanState
from app.schemas import FanStateOut

router = APIRouter(prefix="/api/fan", tags=["fan"])


@router.get("/status", response_model=FanStateOut | None)
def get_fan_status(db: Session = Depends(get_db)):
    return db.query(FanState).first()