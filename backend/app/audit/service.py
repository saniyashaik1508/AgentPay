from sqlalchemy.orm import Session
from app.models import models


def log_event(db: Session, event: str, agent_id: str = None, user_id: str = None,
              transaction_id: str = None, details: dict = None):
    entry = models.AuditLog(
        event=event,
        agent_id=agent_id,
        user_id=user_id,
        transaction_id=transaction_id,
        details=details or {},
    )
    db.add(entry)
    db.commit()
    return entry
