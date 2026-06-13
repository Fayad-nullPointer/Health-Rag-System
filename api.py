"""
Mental Health RAG Chatbot – FastAPI entry point.

This is the slim application shell: it initialises all ML models during
the lifespan startup, wires them into the ``pipeline`` module, mounts
routers and static files, and starts uvicorn.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

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
from memory import ChatMemory

# Routers
from routes.auth_routes import router as auth_router
from routes.chat import router as chat_router

# Pipeline module (we set its globals during lifespan)
import pipeline as pl

from config import EMOTION_MODEL_PATH, REDIS_URL

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan – load all models once at startup ────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise heavy ML models and inject them into the pipeline module."""
    print("Initializing Models and Pipeline... (This may take a moment)")

    # 0. Initialize Cache (non-blocking, degrades gracefully)
    cache = CacheLayer(REDIS_URL)

    # 1. Initialize Classifiers & Clients
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # HuggingFace Inference Client for Whisper STT
    print("Initializing HuggingFace Inference Client...")
    hf_client = InferenceClient(provider="auto", api_key=os.getenv("HF_TOKEN"))
    intents = [
        "greeting", "goodbye", "gratitude",
        "asking_mental_health_question", "self_harm_intent",
        "unsafe_query", "out_of_scope",
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
    emotion_predictor = EmotionPredictor(EMOTION_MODEL_PATH)

    # 2. Initialize Embeddings and Vector DB
    print("Loading Vector Store & RAG Chain...")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )

    vectorstore = QdrantVectorStore(
        client=qdrant_client,
        collection_name="mental_health_index_using_bge-small-en-v1.5",
        embedding=embeddings,
    )

    # Use pure Qdrant retriever for faster startup (BM25 requires loading+chunking the dataset in memory)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # 3. Create RAG Chain
    llm = ChatGroq(
        model_name="llama-3.3-70b-versatile",  # Or mixtral-8x7b-32768
        temperature=0.7,
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

    # ── Wire everything into the pipeline module ──────────────────────
    pl.language_predictor = language_predictor
    pl.emotion_predictor = emotion_predictor
    pl.intent_engine = intent_engine
    pl.rag_chain = rag_chain
    pl.groq_client = groq_client
    pl.hf_client = hf_client
    pl.cache = cache
    pl.memory = ChatMemory(cache)

    print("Pipeline Initialized Successfully!")
    yield


# ── FastAPI app ────────────────────────────────────────────────────────────

app = FastAPI(title="Unified RAG Pipeline & Classifier API", lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (or specify specific ones)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Serve the login page."""
    return FileResponse("static/login.html")


@app.get("/chat")
async def chat_page():
    """Serve the main chat interface."""
    return FileResponse("static/index.html")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
