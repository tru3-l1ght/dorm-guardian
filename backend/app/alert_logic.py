from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Alert


def create_alert_with_cooldown(
    db: Session,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    cooldown_minutes: int = 5,
) -> Alert | None:
    cooldown_start = datetime.utcnow() - timedelta(minutes=cooldown_minutes)

    recent_alert = (
        db.query(Alert)
        .filter(Alert.alert_type == alert_type)
        .filter(Alert.created_at >= cooldown_start)
        .order_by(Alert.created_at.desc())
        .first()
    )

    if recent_alert:
        return None

    alert = Alert(
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
    )

    db.add(alert)
    return alert