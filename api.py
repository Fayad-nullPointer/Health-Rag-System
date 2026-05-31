import os
import json
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Langchain & Qdrant
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from groq import Groq

# Custom Classifiers
# Ensure your PYTHONPATH encompasses the root directory so the classifier module imports correctly.
from classifier.intent_classifier import IntentChatbotEngine
from classifier.language_inference import LanguagePredictor
from classifier.emotion_inference import EmotionPredictor

# Cache layer (gracefully degrades if Redis is unavailable)
from cache_layer import CacheLayer

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup Global State
groq_client = None
intent_engine = None
emotion_predictor = None
language_predictor = None
rag_chain = None
cache = None

from contextlib import asynccontextmanager

# ── Cache TTL constants (seconds) ──────────────────────────────────────────
CACHE_TTL_LANG = 3600       # 1 hour  – same text → same language
CACHE_TTL_EMOTION = 3600    # 1 hour  – same text → same emotion from same model
CACHE_TTL_INTENT = 3600     # 1 hour  – LLM with temp=0 is deterministic
CACHE_TTL_RAG = 1800        # 30 min  – RAG answer freshness

@asynccontextmanager
async def lifespan(app: FastAPI):
    global groq_client, intent_engine, emotion_predictor, language_predictor, rag_chain, cache
    print("Initializing Models and Pipeline... (This may take a moment)")

    # 0. Initialize Cache (non-blocking, degrades gracefully)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache = CacheLayer(redis_url)

    # 1. Initialize Classifiers
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    intents = [
        "greeting", "goodbye", "gratitude", 
        "asking_mental_health_question", "self_harm_intent", 
        "unsafe_query", "out_of_scope"
    ]
    
    # Create a single shared LanguagePredictor instance
    print("Loading Language Predictor...")
    language_predictor = LanguagePredictor()

    print("Loading Intent Classifier...")
    # Inject the shared language_predictor to avoid loading the ~35MB model twice
    intent_engine = IntentChatbotEngine(
        groq_client=groq_client,
        intents=intents,
        language_predictor=language_predictor,
    )
    
    print("Loading Emotion Predictor...")
    emotion_predictor = EmotionPredictor("/media/ahmed-fayad/3b40def2-87b7-41ce-8913-2981f887941c/home/ITI Cont.../NLP and LLM/NLP Final Project/emotion-bert-final")

    # 2. Initialize Embeddings and Vector DB
    print("Loading Vector Store & RAG Chain...")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={'device': 'cpu'}, 
        encode_kwargs={'normalize_embeddings': True} 
    )

    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URL"), 
        api_key=os.getenv("QDRANT_API_KEY")
    )

    vectorstore = QdrantVectorStore(
        client=qdrant_client,
        collection_name="mental_health_index_using_bge-small-en-v1.5",
        embedding=embeddings
    )

    # Use pure Qdrant retriever for faster startup (BM25 requires loading+chunking the dataset in memory)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # 3. Create RAG Chain
    llm = ChatGroq(
        model_name="llama-3.3-70b-versatile", # Or mixtral-8x7b-32768
        temperature=0.7
    )

    system_prompt = (
        "You are a compassionate, professional mental health assistant. "
        "Use the following pieces of retrieved counseling advice to answer the user's question. "
        "If you don't know the answer with the provided context, just say that you don't know, don't try to make up medical advice. "
        "Always maintain an empathetic and supportive tone.\n"
        "IMPORTANT: You MUST reply in the following language: {language}\n\n"
        "Context:\n{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    print("Pipeline Initialized Successfully!")
    yield

# Initialize FastAPI App
app = FastAPI(title="Unified RAG Pipeline & Classifier API", lifespan=lifespan)

# Request / Response Schemas
class ChatRequest(BaseModel):
    user_message: str

class ChatResponse(BaseModel):
    original_message: str
    detected_language: str
    detected_emotion: str
    detected_intent: str
    response: str
    source: str


# ── Thin async wrappers for blocking operations ────────────────────────────

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


async def _run_rag(msg: str, language: str) -> str:
    """Run the full RAG chain (embed → Qdrant → LLM) in a thread."""
    rag_result = await asyncio.to_thread(
        rag_chain.invoke, {"input": msg, "language": language}
    )
    return rag_result["answer"]


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    msg = request.user_message
    msg_hash = CacheLayer.hash_key(msg)

    try:
        # ── 1. Check caches ────────────────────────────────────────────
        cached_lang = cache.get("lang", msg_hash)
        cached_emotion = cache.get("emotion", msg_hash)
        cached_intent = cache.get("intent", msg_hash)

        # ── 2. Build tasks for cache-missed steps (run in parallel) ────
        tasks = {}

        if cached_lang:
            detected_lang = cached_lang["language"]
        else:
            tasks["lang"] = _predict_language(msg)

        if cached_emotion:
            detected_emotion = cached_emotion["label"]
        else:
            tasks["emotion"] = _predict_emotion(msg)

        if cached_intent:
            intent_data = cached_intent
        else:
            tasks["intent"] = _classify_intent(msg)

        # Run all cache-missed steps concurrently
        if tasks:
            keys = list(tasks.keys())
            results = await asyncio.gather(*[tasks[k] for k in keys])
            result_map = dict(zip(keys, results))

            if "lang" in result_map:
                detected_lang = result_map["lang"]
                cache.set("lang", msg_hash, {"language": detected_lang}, CACHE_TTL_LANG)

            if "emotion" in result_map:
                emotion_res = result_map["emotion"]
                detected_emotion = emotion_res[0]["label"] if emotion_res else "unknown"
                emotion_payload = {"label": detected_emotion}
                if emotion_res:
                    emotion_payload["score"] = emotion_res[0].get("score")
                cache.set("emotion", msg_hash, emotion_payload, CACHE_TTL_EMOTION)

            if "intent" in result_map:
                intent_data = result_map["intent"]
                cache.set("intent", msg_hash, intent_data, CACHE_TTL_INTENT)

        intent_name = intent_data.get("intent", "out_of_scope")

        # ── 3. Orchestrate final action based on intent ────────────────
        if intent_name == "asking_mental_health_question":
            # Check RAG cache (keyed on message + language for localised answers)
            rag_cache_key = f"{msg_hash}:{detected_lang}"
            cached_rag = cache.get("rag", rag_cache_key)

            if cached_rag:
                final_answer = cached_rag["answer"]
            else:
                final_answer = await _run_rag(msg, detected_lang)
                cache.set("rag", rag_cache_key, {"answer": final_answer}, CACHE_TTL_RAG)
            source = "RAG Model"
        else:
            # Use the standard fallback router (e.g. self-harm safety message, greeting, etc)
            # Route method returns localized and safe responses built into your engine.
            final_answer = intent_engine.route(msg, intent_data)
            source = f"Intent Engine / Router ({intent_name})"

        return ChatResponse(
            original_message=msg,
            detected_language=str(detected_lang),
            detected_emotion=detected_emotion,
            detected_intent=intent_name,
            response=final_answer,
            source=source
        )

    except Exception as e:
        logger.exception("Error processing chat request")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=FileResponse)
def read_root():
    return "index.html"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
