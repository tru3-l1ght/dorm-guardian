from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert
from app.schemas import AlertOut

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def get_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    include_resolved: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(Alert)

    if not include_resolved:
        query = query.filter(Alert.is_resolved == False)

    return (
        query
        .order_by(Alert.created_at.desc())
        .limit(limit)
        .all()
    )


@router.patch("/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()

    db.commit()
    db.refresh(alert)

    return alert