from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.chatbot_service import process_message
from app.core.security import get_current_user_id
from app.services.chat_service import save_message, get_history
from app.models.user import User


router = APIRouter()


class ChatRequest(BaseModel):
    message: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):

    user = db.query(User).filter(User.id == user_id).first()

    save_message(
        db=db,
        user_id=user_id,
        role="user",
        content=request.message
    )

    history = get_history(
        db=db,
        user_id=user_id,
        limit=8
    )

    history_text = "\n".join(
        f"{msg.role}: {msg.content}"
        for msg in reversed(history)
    )

    result = await process_message(
        request.message,
        history_text,
        user.first_name
    )

    save_message(
        db=db,
        user_id=user_id,
        role="assistant",
        content=result["response"]
    )

    return result