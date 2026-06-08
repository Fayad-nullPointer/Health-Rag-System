# =========================================================
# WHISPER VOICE-TO-TEXT SERVICE
# (HuggingFace Inference API — remote, no local model)
# =========================================================
import asyncio
import os
import logging

from dotenv import load_dotenv
from huggingface_hub import InferenceClient
import re

load_dotenv()

logger = logging.getLogger(__name__)

# =========================================================
# CLIENT (SINGLETON)
# =========================================================

_hf_client = None

# Helper function
def clean_transcription(text: str) -> str:
    """
    Removes unwanted formatting occasionally returned by ASR models:
    - leading microphone emoji
    - surrounding single/double quotes
    - extra whitespace
    """

    if not text:
        return ""

    text = text.strip()

    # Remove leading microphone emoji
    text = re.sub(r"^🎤\s*", "", text)

    # Remove surrounding quotes
    text = re.sub(r'^["\'](.*)["\']$', r"\1", text)

    return text.strip()


def _get_client() -> InferenceClient:
    """
    Lazy-init the HuggingFace InferenceClient (singleton).
    Uses the HF_TOKEN from the .env file.
    """
    global _hf_client

    if _hf_client is None:

        token = os.getenv("HF_TOKEN")

        if not token:
            raise RuntimeError(
                "HF_TOKEN not found in environment variables. "
                "Please set it in your .env file."
            )

        _hf_client = InferenceClient(
            token=token
        )

        logger.info("HuggingFace InferenceClient initialized.")

    return _hf_client


# =========================================================
# TRANSCRIPTION (SYNC)
# =========================================================

def _transcribe_sync(audio_bytes: bytes) -> dict:
    client = _get_client()

    result = client.automatic_speech_recognition(
        audio=audio_bytes,
        model="openai/whisper-large-v3",
    )

    raw_text = result.text if result.text else ""
    transcribed_text = clean_transcription(raw_text)

    logger.info(
        f"Whisper transcription: '{transcribed_text}'"
    )

    return {
        "text": transcribed_text,
        "language": None
    }


# =========================================================
# ASYNC TRANSCRIPTION
# =========================================================

async def transcribe(audio_bytes: bytes) -> dict:
    """
    Async transcription — calls HuggingFace Inference API
    in a thread pool to avoid blocking the event loop.

    Args:
        audio_bytes: Raw audio file bytes (WAV, FLAC, WebM, OGG, etc.)

    Returns:
        dict with keys:
            - text: transcribed text
            - language: detected language (or None)
    """
    return await asyncio.to_thread(
        _transcribe_sync,
        audio_bytes
    )
