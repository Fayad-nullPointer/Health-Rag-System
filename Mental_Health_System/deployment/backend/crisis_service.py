from datetime      import datetime, timezone
from sqlalchemy.orm import Session
from models   import CrisisEvent
from hotlines import get_hotline


def log_crisis_event(
    db           : Session,
    user_id      : int,
    session_id   : str,
    trigger_text : str
) -> CrisisEvent:
    """
    Persists a crisis event to the database.
    Called any time crisis_flag = True in a pipeline response.
    """
    event = CrisisEvent(
        user_id      = user_id,
        session_id   = session_id,
        trigger_text = trigger_text[:1000],   # cap length
        detected_at  = datetime.now(timezone.utc),
        resolved     = False
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event




def get_crisis_context(country: str) -> dict:
    """
    Returns the crisis hotline info for the user's country
    plus the standard crisis text line.
    Used by pipeline.py to enrich the therapist prompt.
    """
    return get_hotline(country)




def get_user_crisis_history(
    db      : Session,
    user_id : int
) -> list[CrisisEvent]:
    return (
        db.query(CrisisEvent)
          .filter(CrisisEvent.user_id == user_id)
          .order_by(CrisisEvent.detected_at.desc())
          .all()
    )
