"""
ML pipeline – model wrappers, caching, and the main chat orchestrator.

Global references (``language_predictor``, ``emotion_predictor``, etc.)
are populated by ``api.py`` during the FastAPI lifespan startup.  Every
async function in this module is safe to call from any route handler.
"""

import asyncio
import logging
import os
import tempfile
from typing import Optional

from config import (
    LANGUAGE_MAP,
    CACHE_TTL_LANG,
    CACHE_TTL_EMOTION,
    CACHE_TTL_INTENT,
    CACHE_TTL_RAG,
)
from cache_layer import CacheLayer
from memory import ChatMemory

logger = logging.getLogger(__name__)

# ── Global references – set by api.py lifespan ────────────────────────────
language_predictor = None
emotion_predictor = None
intent_engine = None
rag_chain = None
groq_client = None
hf_client = None
cache: Optional[CacheLayer] = None
memory: Optional[ChatMemory] = None


# ── Thin async wrappers for blocking operations ───────────────────────────


async def _predict_language(msg: str) -> str:
    """Run sklearn language prediction in a thread."""
    detected_lang = await asyncio.to_thread(language_predictor.predict, msg)
    if isinstance(detected_lang, list):
        detected_lang = detected_lang[0]
    return detected_lang


async def _predict_emotion(msg: str) -> dict:
    """Run BERT emotion inference in a thread."""
    emotion_res = await asyncio.to_thread(emotion_predictor.predict, msg)
    return emotion_res


async def _classify_intent(msg: str) -> dict:
    """Run Groq-backed intent classification in a thread.

    Note: we don't pass language here because language detection runs
    in parallel.  The intent engine will use its shared LanguagePredictor
    internally (same object, no extra memory).
    """
    intent_data = await asyncio.to_thread(intent_engine.classify_intent, msg)
    return intent_data


async def _run_rag(msg: str, language: str, history_context: str = "") -> str:
    """Run the full RAG chain (embed → Qdrant → LLM) in a thread.

    If ``history_context`` is provided it is prepended to the user
    message so the LLM can reference previous turns.
    """
    if history_context:
        rag_input = (
            f"Previous conversation:\n{history_context}\n\nCurrent message: {msg}"
        )
    else:
        rag_input = msg

    rag_result = await asyncio.to_thread(
        rag_chain.invoke, {"input": rag_input, "language": language}
    )
    return rag_result["answer"]


async def _transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    """Transcribe audio bytes via HuggingFace Whisper API in a thread."""
    suffix = os.path.splitext(filename)[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        result = await asyncio.to_thread(
            hf_client.automatic_speech_recognition,
            tmp.name,
            model="openai/whisper-large-v3",
        )
    # result can be a string or an object with .text
    return result.text if hasattr(result, "text") else str(result)


# ── Main orchestrator ─────────────────────────────────────────────────────


async def process_chat_message(msg: str, user_id: str) -> dict:
    """Run the full chat pipeline for a single user message.

    Steps:
        1. Hash the message for cache lookups.
        2. Check caches for language / emotion / intent.
        3. Build parallel async tasks for any cache misses.
        4. ``asyncio.gather`` the cache-miss tasks.
        5. Store freshly computed results in the cache.
        6. Retrieve conversation history from memory.
        7. Route by intent (mental_health → RAG, self_harm → rescue,
           other → intent router).
        8. Persist user + assistant messages in memory.
        9. Return a result dict.

    Returns:
        A dict with keys: ``original_message``, ``detected_language``,
        ``detected_emotion``, ``detected_intent``, ``response``, ``source``.
    """
    logger.info(
        "Processing chat message for user: %s (msg length: %d)", user_id, len(msg)
    )
    msg_hash = CacheLayer.hash_key(msg)

    # ── 1. Check caches ────────────────────────────────────────────────
    cached_lang = cache.get("lang", msg_hash)
    cached_emotion = cache.get("emotion", msg_hash)
    cached_intent = cache.get("intent", msg_hash)

    # ── 2. Build tasks for cache-missed steps (run in parallel) ────────
    tasks: dict = {}

    if cached_lang:
        detected_lang = cached_lang["language"]
        logger.info("Language cache HIT for message: %s", detected_lang)
    else:
        logger.info("Language cache MISS, queueing prediction")
        tasks["lang"] = _predict_language(msg)

    if cached_emotion:
        detected_emotion = cached_emotion["label"]
        logger.info("Emotion cache HIT for message: %s", detected_emotion)
    else:
        logger.info("Emotion cache MISS, queueing prediction")
        tasks["emotion"] = _predict_emotion(msg)

    if cached_intent:
        intent_data = cached_intent
        logger.info("Intent cache HIT for message: %s", intent_data.get("intent"))
    else:
        logger.info("Intent cache MISS, queueing classification")
        tasks["intent"] = _classify_intent(msg)

    # ── 3-4. Run all cache-missed steps concurrently ───────────────────
    if tasks:
        logger.info("Executing %d cache-miss prediction tasks concurrently", len(tasks))
        keys = list(tasks.keys())
        results = await asyncio.gather(*[tasks[k] for k in keys])
        result_map = dict(zip(keys, results))

        if "lang" in result_map:
            detected_lang = result_map["lang"]
            logger.info("Detected language: %s", detected_lang)
            cache.set("lang", msg_hash, {"language": detected_lang}, CACHE_TTL_LANG)

        if "emotion" in result_map:
            emotion_res = result_map["emotion"]
            detected_emotion = emotion_res[0]["label"] if emotion_res else "unknown"
            logger.info("Detected emotion: %s", detected_emotion)
            emotion_payload: dict = {"label": detected_emotion}
            if emotion_res:
                emotion_payload["score"] = emotion_res[0].get("score")
            cache.set("emotion", msg_hash, emotion_payload, CACHE_TTL_EMOTION)

        if "intent" in result_map:
            intent_data = result_map["intent"]
            logger.info(
                "Detected intent: %s (confidence: %s)",
                intent_data.get("intent"),
                intent_data.get("confidence"),
            )
            cache.set("intent", msg_hash, intent_data, CACHE_TTL_INTENT)

    intent_name = intent_data.get("intent", "out_of_scope")
    full_language_name = LANGUAGE_MAP.get(detected_lang, detected_lang)

    # ── 5. Get memory history ──────────────────────────────────────────
    history_context = ""
    if memory is not None:
        history_context = memory.format_for_prompt(user_id)

    # ── 6. Orchestrate final action based on intent ────────────────────
    logger.info(
        "Routing query for user %s with intent: %s, language: %s",
        user_id,
        intent_name,
        full_language_name,
    )
    if intent_name == "asking_mental_health_question":
        # Check RAG cache (keyed on message + language for localised answers)
        rag_cache_key = f"{msg_hash}:{detected_lang}"
        cached_rag = cache.get("rag", rag_cache_key)

        if cached_rag:
            logger.info("RAG cache HIT")
            final_answer = cached_rag["answer"]
        else:
            logger.info("RAG cache MISS, running RAG pipeline...")
            final_answer = await _run_rag(msg, full_language_name, history_context)
            cache.set("rag", rag_cache_key, {"answer": final_answer}, CACHE_TTL_RAG)
        source = "RAG Model"

    elif intent_name == "self_harm_intent":
        logger.warning("CRITICAL: Self-harm intent detected for user: %s", user_id)
        # Try to rescue patient with a highly empathetic, supportive message
        rescue_cache_key = f"rescue:{msg_hash}:{detected_lang}"
        cached_rescue = cache.get("rescue", rescue_cache_key)

        if cached_rescue:
            logger.info("Rescue response cache HIT")
            final_answer = cached_rescue["answer"]
        else:
            logger.info(
                "Rescue response cache MISS, calling emergency rescue generator..."
            )
            prompt_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a compassionate, professional mental health assistant. "
                        "The user has indicated self-harm or suicidal intent. Your immediate "
                        "goal is to try to rescue the patient. Start by expressing deep empathy "
                        "and explicitly stating that you are very sad to hear they are feeling "
                        "this way and experiencing such pain. After validating their feelings, "
                        "provide a supportive and urgent message strongly encouraging them to "
                        "reach out for immediate help. Provide international crisis hotline "
                        "numbers such as 988 (US/Canada), 111 or 999 (UK), 112 / 122 / 123 "
                        "for the Middle East and Europe, and recommend visiting "
                        "findahelpline.com for local support. Suggest they go to the nearest "
                        "hospital. Do not provide any counseling beyond this immediate rescue "
                        "intervention. IMPORTANT: You MUST reply ENTIRELY in the following "
                        f"language: {full_language_name}. DO NOT include any characters, "
                        "words, or phrases from any other language (e.g. absolutely no "
                        "Chinese characters if the language is Arabic)."
                    ),
                },
                {"role": "user", "content": msg},
            ]
            response = await asyncio.to_thread(
                groq_client.chat.completions.create,
                model="openai/gpt-oss-120b",
                temperature=0.1,  # strict low temperature to avoid hallucinating foreign characters
                messages=prompt_messages,
            )
            final_answer = response.choices[0].message.content
            cache.set(
                "rescue", rescue_cache_key, {"answer": final_answer}, CACHE_TTL_RAG
            )
        source = "Emergency Rescue System"

    else:
        logger.info("Handling general intent: %s with Locale Router", intent_name)
        # Use the standard fallback router (e.g. greeting, etc.)
        # Route method returns localized and safe responses built into your engine.
        final_answer = intent_engine.route(msg, intent_data)
        source = f"Intent Engine / Router ({intent_name})"

    # ── 7. Persist to memory ───────────────────────────────────────────
    if memory is not None:
        logger.info(
            "Persisting message and response to chat memory for user: %s", user_id
        )
        memory.add_message(user_id, "user", msg)
        memory.add_message(user_id, "assistant", final_answer)

    return {
        "original_message": msg,
        "detected_language": str(detected_lang),
        "detected_emotion": detected_emotion,
        "detected_intent": intent_name,
        "response": final_answer,
        "source": source,
    }
