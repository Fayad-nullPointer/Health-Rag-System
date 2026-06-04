"""
Chat routes – text and voice endpoints (authentication required).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from auth import get_current_user
import pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


# ── Request / Response schemas ─────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Body for the text chat endpoint."""
    user_message: str


class ChatResponse(BaseModel):
    """Standard chat response with all pipeline outputs."""
    original_message: str
    detected_language: str
    detected_emotion: str
    detected_intent: str
    response: str
    source: str


class VoiceChatResponse(ChatResponse):
    """Extended response that also includes the transcribed audio text."""
    transcribed_text: str


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, user: dict = Depends(get_current_user)):
    """Process a text chat message through the full ML pipeline."""
    try:
        result = await pipeline.process_chat_message(request.user_message, user["username"])
        return ChatResponse(**result)
    except Exception as e:
        logger.exception("Error processing chat request")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/voice", response_model=VoiceChatResponse)
async def voice_chat_endpoint(
    audio: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Accept an audio file, transcribe it with Whisper, then run the chat pipeline."""
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # 1. Transcribe
        transcribed_text = await pipeline._transcribe_audio(
            audio_bytes, audio.filename or "audio.webm"
        )
        transcribed_text = transcribed_text.strip()
        if not transcribed_text:
            raise HTTPException(
                status_code=400, detail="Could not transcribe any speech from audio"
            )

        logger.info("Transcribed voice input: %s", transcribed_text[:100])

        # 2. Run the same chat pipeline with the transcribed text
        result = await pipeline.process_chat_message(transcribed_text, user["username"])

        # 3. Return extended response with transcription
        return VoiceChatResponse(transcribed_text=transcribed_text, **result)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing voice chat request")
        raise HTTPException(status_code=500, detail=str(e))
