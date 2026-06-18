from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from threading import Thread
import logging

from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.voice import router as voice_router

from app.core.database import Base, engine
from rag.rag_pipeline import initialize_rag
from rag.rag_state import RAG_READY_EVENT


# -----------------------------------------------------
# LOGGING
# -----------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------
# RAG BOOTSTRAP (NON-BLOCKING)
# -----------------------------------------------------
def boot_rag():
    try:
        logger.info("Initializing RAG...")
        initialize_rag()
        logger.info("RAG READY")
    except Exception as e:
        logger.exception(f"RAG initialization failed: {e}")


# -----------------------------------------------------
# LIFESPAN
# -----------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Serenity API...")

    # DB setup
    Base.metadata.create_all(bind=engine)

    # Start RAG in background thread (non-blocking)
    thread = Thread(target=boot_rag, daemon=True)
    thread.start()

    logger.info("API is running while RAG initializes...")

    yield

    logger.info("Shutting down Serenity API...")


# -----------------------------------------------------
# APP
# -----------------------------------------------------
app = FastAPI(
    title="Serenity",
    lifespan=lifespan,
)


# Temp: Local host
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
    ],
    allow_origin_regex=r"https://serenity.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# vercel integration

# app.add_middleware(
#     CORSMiddleware,
#     allow_origin_regex=r"https://serenity.*\.vercel\.app",
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# Routers
app.include_router(chat_router)
app.include_router(auth_router, prefix="/auth")
app.include_router(voice_router)


# -----------------------------------------------------
# BASIC ENDPOINTS
# -----------------------------------------------------
@app.get("/")
def home():
    return {
        "message": "Serenity AI API is running",
        "status": "success",
    }


@app.get("/health")
def health():
    return {
        "status": "OK",
        "rag_ready": RAG_READY_EVENT.is_set(),
        "service": "Serenity Mental Health",
    }


@app.get("/login")
def login_page():
    return {
        "message": "Login page endpoint",
        "endpoint": "/auth/login",
    }


@app.get("/register")
def register_page():
    return {
        "message": "Register page endpoint",
        "endpoint": "/auth/register",
    }


@app.get("/chat")
def chat_page():
    return {
        "message": "Chat endpoint available",
        "endpoint": "/chat",
    }
