from pydantic import BaseModel, field_validator
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import asyncio
import logging

from app.core.database import SessionLocal
from app.services.chatbot_service import process_message
from app.core.security import get_current_user_id
from app.services.chat_service import save_message, get_history
from app.models.user import User
from rag.rag_state import RAG_READY_EVENT


logger = logging.getLogger(__name__)

router = APIRouter()


# -------------------------------------------------
# REQUEST MODEL
# -------------------------------------------------
class ChatRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str):
        if not v or not v.strip():
            raise ValueError("message cannot be empty or whitespace only")
        return v.strip()


# -------------------------------------------------
# DB SESSION
# -------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------
# THREADSAFE HELPERS
# -------------------------------------------------
def save_message_threadsafe(user_id, role, content):
    db = SessionLocal()
    try:
        return save_message(db=db, user_id=user_id, role=role, content=content)
    finally:
        db.close()


def get_history_threadsafe(user_id, limit=8):
    db = SessionLocal()
    try:
        return get_history(db=db, user_id=user_id, limit=limit)
    finally:
        db.close()


# -------------------------------------------------
# CHAT ENDPOINT
# -------------------------------------------------
@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    # -------------------------------------------------
    # HARD GATE: RAG not ready yet
    # -------------------------------------------------
    if not RAG_READY_EVENT.is_set():
        return {"response": "System is starting up, please try again in a few seconds."}

    try:
        # -------------------------------------------------
        # GET USER
        # -------------------------------------------------
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        # -------------------------------------------------
        # PARALLEL: save message + fetch history
        # -------------------------------------------------
        save_task = asyncio.to_thread(
            save_message_threadsafe,
            user_id,
            "user",
            request.message,
        )

        history_task = asyncio.to_thread(
            get_history_threadsafe,
            user_id,
            4,
        )

        _, history = await asyncio.gather(save_task, history_task)

        history_text = "\n".join(
            f"{msg.role}: {msg.content}" for msg in reversed(history)
        )

        logger.info("=== CHAT HISTORY SENT TO MODEL ===")
        logger.info(history_text)
        logger.info("===================================")

        # -------------------------------------------------
        # LLM / RAG PROCESSING
        # -------------------------------------------------
        result = await process_message(
            request.message,
            history_text,
            user.first_name,
            user.country,
        )

        # -------------------------------------------------
        # SAVE ASSISTANT RESPONSE (ASYNC)
        # -------------------------------------------------
        await asyncio.to_thread(
            save_message,
            db=db,
            user_id=user_id,
            role="assistant",
            content=result["response"],
        )

        return {"response": result["response"]}

    except Exception as e:
        logger.exception("Chat endpoint failed")
        return {
            "error": "Internal server error",
            "details": str(e),
        }
