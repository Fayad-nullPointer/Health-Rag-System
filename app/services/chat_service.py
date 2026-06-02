from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage


def save_message(
    db: Session,
    user_id: int,
    role: str,
    content: str
):
    message = ChatMessage(
        user_id=user_id,
        role=role,
        content=content
    )

    db.add(message)
    db.commit()

    return message


def get_history(
    db: Session,
    user_id: int,
    limit: int = 10
):
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )