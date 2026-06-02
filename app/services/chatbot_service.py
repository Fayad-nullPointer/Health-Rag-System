# =========================================================
# IMPORTS
# =========================================================
import os
import json
import logging
import uuid
from logging.handlers import RotatingFileHandler

from groq import Groq
from dotenv import load_dotenv

from rag.rag_pipeline import rag_pipeline
from classifier import (
    emotion_inference,
    language_inference,
    intent_classifier
)
from rag.crisis_handler import handle_self_harm

# =========================================================
# CONFIG
# =========================================================
load_dotenv("config/.env")

DEBUG_MODE = True

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# =========================================================
# HANDLERS
# =========================================================

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

file_handler = RotatingFileHandler(
    filename=os.path.join(LOG_DIR, "app.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# =========================================================
# HELPERS (NEW)
# =========================================================
def log_event(event_type: str, data: dict):
    logger.info(json.dumps({
        "event": event_type,
        **data
    }, ensure_ascii=False, default=str))


def log_debug_safe(label: str, data: dict):
    """Avoid dumping huge unsafe logs unless needed"""
    logger.debug(f"{label}: {json.dumps(data, ensure_ascii=False, default=str)}")

# =========================================================
# CLIENTS
# =========================================================
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

language_model = language_inference.LanguagePredictor()
emotion_model = emotion_inference.EmotionClassifier()

# =========================================================
# INTENTS
# =========================================================
INTENTS = [
    "greeting",
    "goodbye",
    "gratitude",
    "asking_mental_health_question",
    "out_of_scope",
    "unsafe_query",
    "self_harm_intent"
]

engine = intent_classifier.IntentChatbotEngine(
    groq_client=client,
    intents=INTENTS
)

# =========================================================
# MAIN SERVICE
# =========================================================
def process_message(message: str, chat_history: str = ""):

    trace_id = str(uuid.uuid4())

    logger.info("=" * 80)
    logger.info(f"TRACE_ID: {trace_id}")
    logger.info("NEW USER MESSAGE")

    log_event("input", {
        "trace_id": trace_id,
        "message_length": len(message)
    })

    # -----------------------------------------------------
    # LANGUAGE
    # -----------------------------------------------------
    language = str(language_model.predict(message))
    log_event("language_detection", {
        "trace_id": trace_id,
        "language": language
    })

    # -----------------------------------------------------
    # EMOTION
    # -----------------------------------------------------
    emotion = emotion_model.predict(message)["emotion"]
    log_event("emotion_detection", {
        "trace_id": trace_id,
        "emotion": emotion
    })

    # -----------------------------------------------------
    # INTENT
    # -----------------------------------------------------
    intent_data = engine.classify_intent(
        user_message=message,
        language=language
    )

    intent_data = engine.apply_confidence_threshold(intent_data)
    intent = intent_data["intent"]

    log_event("intent_classification", {
        "trace_id": trace_id,
        **intent_data
    })

    # -----------------------------------------------------
    # ROUTING
    # -----------------------------------------------------
    metadata = None

    if intent == "self_harm_intent":

        logger.info("Route: Crisis Handler")

        response = handle_self_harm(message, language)

    elif intent == "asking_mental_health_question":

        logger.info("Route: RAG Pipeline")

        metadata = rag_pipeline(
            query=message,
            language=language,
            emotion=emotion,
            chat_history=chat_history,
            return_metadata=True
        )

        response = metadata["response"]

        log_event("rag_result", {
            "trace_id": trace_id,
            "retrieval_quality": metadata.get("retrieval_quality"),
            "contexts_count": len(metadata.get("retrieved_contexts", [])),
            "response_length": len(metadata.get("response", ""))
        })

        if DEBUG_MODE:
            log_debug_safe("RAG_METADATA_FULL", metadata)

    else:

        logger.info("Route: Intent Response")

        response = engine.build_response(
            intent=intent,
            language=language
        )

    # -----------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------
    logger.info(f"RESPONSE: {response}")
    logger.info("=" * 80)

    result = {
        "trace_id": trace_id,
        "intent": intent,
        "language": language,
        "emotion": emotion,
        "response": response
    }

    if DEBUG_MODE and metadata:
        result["debug"] = metadata

    return result