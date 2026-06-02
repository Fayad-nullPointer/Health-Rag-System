from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from torch import histc

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
def chat(request: ChatRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    # get current loggedin user
    user = db.query(User).filter(User.id == user_id).first()
    first_name = user.first_name

    # 1. save message per user
    save_message(db=db, 
                 user_id=user_id, 
                 role="user", 
                 content=request.message)

    # 2. get user messages history
    history = get_history(db=db, 
                          user_id=user_id, 
                          limit=8)

    # 3. convert chat history to readable text from recent to older one
    history_text = "\n".join([
        f"{msg.role}: {msg.content}"
        for msg in reversed(history)
    ])

    # 4. send message plus history to the rag
    result = process_message(
        request.message,
        chat_history=history_text,
        user_name=first_name
    )

    # 5. save chatbot response
    save_message(
        db=db,
        user_id=user_id,
        role="assistant",
        content=result["response"]
    )

    return result