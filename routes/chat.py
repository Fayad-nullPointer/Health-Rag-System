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

    user_message: str = None
    message: str = None

    def get_message(self):
        """Get the message from either field (backward compatibility)."""
        return self.user_message or self.message


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


class FeedbackRequest(BaseModel):
    """Body for the feedback endpoint."""

    vote: str  # "up" or "down"
    user_message: str
    bot_response: str


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, user: dict = Depends(get_current_user)):
    """Process a text chat message through the full ML pipeline."""
    logger.info("Received chat request from user: %s", user["username"])
    try:
        message = request.get_message()
        if not message:
            logger.warning(
                "Chat request from user %s failed: Empty message", user["username"]
            )
            raise HTTPException(status_code=400, detail="No message provided")
        result = await pipeline.process_chat_message(message, user["username"])
        logger.info(
            "Successfully processed chat request for user: %s", user["username"]
        )
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
    logger.info(
        "Received voice request from user: %s, file: %s",
        user["username"],
        audio.filename,
    )
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            logger.warning(
                "Voice request from user %s failed: Empty audio file", user["username"]
            )
            raise HTTPException(status_code=400, detail="Empty audio file")

        # 1. Transcribe
        transcribed_text = await pipeline._transcribe_audio(
            audio_bytes, audio.filename or "audio.webm"
        )
        transcribed_text = transcribed_text.strip()
        if not transcribed_text:
            logger.warning(
                "Voice request from user %s failed: Could not transcribe speech",
                user["username"],
            )
            raise HTTPException(
                status_code=400, detail="Could not transcribe any speech from audio"
            )

        logger.info("Transcribed voice input: %s", transcribed_text[:100])

        # 2. Run the same chat pipeline with the transcribed text
        result = await pipeline.process_chat_message(transcribed_text, user["username"])

        # 3. Return extended response with transcription
        logger.info(
            "Successfully processed voice chat request for user: %s", user["username"]
        )
        return VoiceChatResponse(transcribed_text=transcribed_text, **result)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing voice chat request")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def feedback_endpoint(request: FeedbackRequest):
    """
    Accept feedback on bot responses (vote: up/down).
    This endpoint can optionally log feedback for model improvement.
    """
    try:
        # Log feedback for potential future analysis
        logger.info(
            f"Feedback received - Vote: {request.vote}, "
            f"User message: {request.user_message[:50]}..., "
            f"Bot response: {request.bot_response[:50]}..."
        )

        # Optional: Store feedback in cache/database for analysis
        if hasattr(pipeline, "cache") and pipeline.cache:
            feedback_key = f"feedback:{request.vote}:{hash(request.user_message)}"
            try:
                pipeline.cache.set(
                    feedback_key,
                    {
                        "vote": request.vote,
                        "user_message": request.user_message,
                        "bot_response": request.bot_response,
                    },
                    ttl=86400,
                )  # Store for 24 hours
            except Exception:
                pass  # Cache is optional, don't fail the endpoint

        return {"status": "success", "message": "Feedback recorded"}
    except Exception as e:
        logger.exception("Error processing feedback")
        raise HTTPException(status_code=500, detail=str(e))
