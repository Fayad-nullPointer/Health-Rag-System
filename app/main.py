from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.voice import router as voice_router

from app.core.database import Base, engine


from contextlib import asynccontextmanager
from rag.rag_pipeline import initialize_rag


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("Initializing RAG...")

    initialize_rag()

    Base.metadata.create_all(bind=engine)

    print("RAG Ready.")

    yield

    print("Shutting down...")


app = FastAPI(title="Serenity", lifespan=lifespan)


app.include_router(chat_router)
app.include_router(auth_router, prefix="/auth")
app.include_router(voice_router)


# Endpoints


@app.get("/")
def home():
    return {"message": "MindCare AI API is running", "status": "success"}


@app.get("/health")
def health():
    return {"status": "healthy", "service": "MindCare AI"}


@app.get("/login")
def login_page():
    return {"message": "Login page endpoint", "endpoint": "/auth/login"}


@app.get("/register")
def register_page():
    return {"message": "Register page endpoint", "endpoint": "/auth/register"}


@app.get("/chat")
def chat_page():
    return {"message": "Chat endpoint available", "endpoint": "/chat"}
