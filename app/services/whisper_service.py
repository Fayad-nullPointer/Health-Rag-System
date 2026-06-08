# =========================================================
# WHISPER VOICE-TO-TEXT SERVICE
# (HuggingFace Inference API — remote, no local model)
# =========================================================
import asyncio
import os
import logging

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

logger = logging.getLogger(__name__)

# =========================================================
# CLIENT (SINGLETON)
# =========================================================

_hf_client = None


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
    """
    Synchronous transcription using HuggingFace Inference API.
    Sends audio bytes to the Whisper model hosted on HF servers.

    Returns dict with 'text' and 'language' keys.
    """
    client = _get_client()

    result = client.automatic_speech_recognition(
        audio=audio_bytes,
        model="openai/whisper-large-v3",
    )

    transcribed_text = result.text.strip() if result.text else ""

    logger.info(
        f"Whisper transcription: '{transcribed_text}'"
    )

    return {
        "text": transcribed_text,
        "language": None  # Language will be detected by the text classifier
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
