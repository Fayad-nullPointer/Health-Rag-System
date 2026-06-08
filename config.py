"""
Centralized configuration for the Mental Health RAG Chatbot.

All constants, environment variables, and tunable parameters live here
so they can be imported by any module without circular dependencies.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Cache TTL constants (seconds) ──────────────────────────────────────────
CACHE_TTL_LANG = 3600       # 1 hour  – same text → same language
CACHE_TTL_EMOTION = 3600    # 1 hour  – same text → same emotion from same model
CACHE_TTL_INTENT = 3600     # 1 hour  – LLM with temp=0 is deterministic
CACHE_TTL_RAG = 1800        # 30 min  – RAG answer freshness
CACHE_TTL_MEMORY = 86400    # 24 hours for chat history

# ── Language map ───────────────────────────────────────────────────────────
LANGUAGE_MAP = {
    "ar": "Arabic", "en": "English", "es": "Spanish", "fr": "French",
    "de": "German", "it": "Italian", "pt": "Portuguese", "ru": "Russian",
    "zh": "Chinese", "ja": "Japanese", "hi": "Hindi", "tr": "Turkish",
    "nl": "Dutch", "pl": "Polish", "vi": "Vietnamese", "th": "Thai",
    "sw": "Swahili", "ur": "Urdu", "el": "Greek", "bg": "Bulgarian",
}

# ── Paths ──────────────────────────────────────────────────────────────────
EMOTION_MODEL_PATH = os.getenv(
    "EMOTION_MODEL_PATH",
    "/media/ahmed-fayad/3b40def2-87b7-41ce-8913-2981f887941c/home/ITI Cont.../NLP and LLM/NLP Final Project/emotion-bert-final",
)

# ── JWT ────────────────────────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-in-production-mental-health-app-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# ── Redis ──────────────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ── API Keys ──────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# ── Chat memory ───────────────────────────────────────────────────────────
MAX_MEMORY_MESSAGES = 10
