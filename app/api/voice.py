import asyncio
import logging

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_current_user_id
from app.services.whisper_service import transcribe
from app.services.chatbot_service import process_message
from app.services.chat_service import save_message, get_history
from app.models.user import User


logger = logging.getLogger(__name__)

router = APIRouter()


# =========================================================
# DB DEPENDENCY
# =========================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================================================
# VOICE ENDPOINT
# =========================================================

@router.post("/voice")
async def voice_chat(
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Accepts an audio file upload, transcribes it with Whisper,
    then feeds the transcribed text into the chatbot pipeline.

    Returns the same response format as /chat plus:
    - transcribed_text: what Whisper heard
    - voice_language: language detected from voice (if any)
    """

    # -------------------------------------------------
    # READ AUDIO
    # -------------------------------------------------
    audio_bytes = await audio.read()

    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty audio file"
        )

    logger.info(
        f"Voice upload: {audio.filename}, "
        f"size={len(audio_bytes)} bytes, "
        f"type={audio.content_type}"
    )

    # -------------------------------------------------
    # TRANSCRIBE (ASYNC)
    # -------------------------------------------------
    transcription = await transcribe(audio_bytes)

    transcribed_text = transcription["text"]

    if not transcribed_text or transcribed_text.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Could not transcribe audio. Please try again."
        )

    # -------------------------------------------------
    # GET USER + DB OPS (PARALLEL)
    # -------------------------------------------------
    user = db.query(User).filter(User.id == user_id).first()

    save_task = asyncio.to_thread(
        save_message,
        db, user_id, "user", f"🎤 {transcribed_text}"
    )

    history_task = asyncio.to_thread(
        get_history,
        db, user_id, 8
    )

    _, history = await asyncio.gather(save_task, history_task)

    history_text = "\n".join(
        f"{msg.role}: {msg.content}"
        for msg in reversed(history)
    )

    # -------------------------------------------------
    # PROCESS MESSAGE (EXISTING PIPELINE)
    # -------------------------------------------------
    result = await process_message(
        transcribed_text,
        history_text,
        user.first_name if user else None
    )

    # -------------------------------------------------
    # SAVE ASSISTANT RESPONSE
    # -------------------------------------------------
    await asyncio.to_thread(
        save_message,
        db, user_id, "assistant", result["response"]
    )

    # -------------------------------------------------
    # ADD VOICE-SPECIFIC FIELDS
    # -------------------------------------------------
    result["transcribed_text"] = transcribed_text
    result["voice_language"] = transcription.get("language")
    result["input_type"] = "voice"

    return result
