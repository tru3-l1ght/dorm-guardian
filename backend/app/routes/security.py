from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SecurityEvent
from app.schemas import SecurityEventOut

router = APIRouter(prefix="/api/security", tags=["security"])


@router.get("/events", response_model=list[SecurityEventOut])
def get_security_events(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return (
        db.query(SecurityEvent)
        .order_by(SecurityEvent.created_at.desc())
        .limit(limit)
        .all()
    )