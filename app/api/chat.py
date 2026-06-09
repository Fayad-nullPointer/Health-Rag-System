from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import asyncio

from app.core.database import SessionLocal
from app.services.chatbot_service import process_message
from app.core.security import get_current_user_id
from app.services.chat_service import save_message, get_history
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

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

    # -------------------------------------------------
    # PARALLEL: save user message + fetch history
    # -------------------------------------------------
    save_task = asyncio.to_thread(
        save_message,
        db=db,
        user_id=user_id,
        role="user",
        content=request.message
    )

    history_task = asyncio.to_thread(
        get_history,
        db=db,
        user_id=user_id,
        limit=8
    )

    _, history = await asyncio.gather(save_task, history_task)

    history_text = "\n".join(
        f"{msg.role}: {msg.content}"
        for msg in reversed(history)
    )

    logger.info("=== CHAT HISTORY SENT TO MODEL ===")
    logger.info(history_text)
    logger.info("===================================")

    result = await process_message(
        request.message,
        history_text,
        user.first_name
    )

    # -------------------------------------------------
    # ASYNC: save assistant response
    # -------------------------------------------------
    await asyncio.to_thread(
        save_message,
        db=db,
        user_id=user_id,
        role="assistant",
        content=result["response"]
    )

    return result