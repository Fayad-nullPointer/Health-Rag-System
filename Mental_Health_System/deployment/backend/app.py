import multiprocessing
multiprocessing.set_start_method('spawn', force=True)

import os
import uuid
from typing    import Optional
from contextlib import asynccontextmanager

from fastapi             import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses   import FileResponse
from pydantic            import BaseModel, EmailStr
from sqlalchemy          import create_engine
from sqlalchemy.orm      import sessionmaker, Session
from dotenv              import load_dotenv

from models         import Base, User, ChatSession, Message, create_tables
from auth           import (
    RegisterRequest, LoginRequest, TokenResponse, UserOut,
    create_user, get_user_by_email, verify_password,
    create_access_token, decode_access_token, hash_password,
    oauth2_scheme
)
from session_store  import session_store
from crisis_service import log_crisis_event
from hotlines       import get_hotline, list_supported_countries
from pipeline       import run_pipeline

load_dotenv()


# ==========================================
# Database Setup
# ==========================================

DATABASE_URL = "sqlite:///./mental_health.db"
engine       = create_engine(DATABASE_URL, connect_args = {"check_same_thread": False})
SessionLocal = sessionmaker(autocommit = False, autoflush = False, bind = engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# Lifespan Management (Prevents Windows Crash)
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executes once on startup, shielding the reloader subprocess
    create_tables()
    yield


# ==========================================
# App Configuration
# ==========================================

app = FastAPI(
    title = "Mental Health Support Chatbot", 
    version = "1.0.0",
    lifespan = lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"]
)

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory = os.path.join(FRONTEND_DIR, "assets")),
              name="assets")


# ==========================================
# Auth Dependency
# ==========================================

def get_current_user(
    token : str     = Depends(oauth2_scheme),
    db    : Session = Depends(get_db)
) -> User:
    
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail      = "Invalid or expired token",
        headers     = {"WWW-Authenticate": "Bearer"}
    )

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception
    user_id = payload.get("sub")

    if not user_id:
        raise credentials_exception
    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user or not user.is_active:
        raise credentials_exception
    
    return user


# ==========================================
# Pydantic Schemas
# ==========================================

class ChatRequest(BaseModel):
    message    : str
    session_id : Optional[str] = None


class ChatResponse(BaseModel):
    answer        : str
    session_id    : str
    emotion       : Optional[str]
    emotion_conf  : Optional[float]
    language      : str
    intent        : str
    crisis_flag   : bool
    action_taken  : str
    quality_score : int
    latency_ms    : float
    sources       : list
    hotline       : Optional[dict] = None
    timings       : Optional[dict] = None


class SessionSummaryOut(BaseModel):
    session_id    : str
    turn_count    : int
    started_at    : str
    last_active   : str
    prior_crisis  : bool
    emotion_history : list
    topics_discussed: list


# ==========================================
# Frontend Routes (Clean Routing Mappings)
# ==========================================

@app.get("/")
def serve_landing():
    path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"message": "Mental Health Support API is running"}


@app.get("/chat")
def serve_chat():
    return FileResponse(os.path.join(FRONTEND_DIR, "chat.html"))


@app.get("/login")
def serve_login():
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))


@app.get("/register")
def serve_register():
    return FileResponse(os.path.join(FRONTEND_DIR, "register.html"))


# ==========================================
# Auth Routes
# ==========================================

@app.post("/auth/register", response_model = TokenResponse, tags = ["Auth"])
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    user  = create_user(db, data)
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, username=user.username,
                         country=user.country)


@app.post("/auth/login", response_model = TokenResponse, tags = ["Auth"])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, data.email)
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, username=user.username,
                         country=user.country)


@app.get("/auth/me", response_model = UserOut, tags = ["Auth"])
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ==========================================
# Chat Route
# ==========================================

@app.post("/chat", response_model = ChatResponse, tags = ["Chat"])
def chat(
    req          : ChatRequest,
    db           : Session = Depends(get_db),
    current_user : User    = Depends(get_current_user)
):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Get or create session memory
    session = session_store.get_or_create(
        session_id = req.session_id,
        user_id    = current_user.id,
        country    = current_user.country
    )

    # Ensure ChatSession row exists in DB
    db_session = db.query(ChatSession).filter(
        ChatSession.session_id == session.session_id
    ).first()
    if not db_session:
        db_session = ChatSession(
            session_id = session.session_id,
            user_id    = current_user.id
        )
        db.add(db_session)
        db.commit()

    # Run the full pipeline
    result = run_pipeline(
        query   = req.message.strip(),
        session = session,
        country = current_user.country
    )

    # Persist both messages to DB
    db.add(Message(
        session_id   = session.session_id,
        role         = "user",
        content      = req.message.strip(),
        emotion      = result.get("emotion"),
        emotion_conf = result.get("emotion_conf"),
        language     = result.get("language"),
        intent       = result.get("intent"),
        crisis_flag  = result.get("crisis_flag", False)
    ))
    db.add(Message(
        session_id  = session.session_id,
        role        = "assistant",
        content     = result["answer"],
        crisis_flag = result.get("crisis_flag", False)
    ))

    # Update session turn count
    db_session.turn_count += 1
    db.commit()

    # Log crisis event if triggered
    if result.get("crisis_flag"):
        log_crisis_event(
            db           = db,
            user_id      = current_user.id,
            session_id   = session.session_id,
            trigger_text = req.message.strip()
        )

    # Attach hotline info if crisis
    hotline = None
    if result.get("crisis_flag"):
        hotline = get_hotline(current_user.country)

    return ChatResponse(
        answer        = result["answer"],
        session_id    = session.session_id,
        emotion       = result.get("emotion"),
        emotion_conf  = result.get("emotion_conf"),
        language      = result.get("language", "en"),
        intent        = result.get("intent", "asking_mental_health_question"),
        crisis_flag   = result.get("crisis_flag", False),
        action_taken  = result.get("action_taken", "answer"),
        quality_score = result.get("quality_score", 3),
        latency_ms    = result.get("latency_ms", 0),
        sources       = result.get("sources", []),
        hotline       = hotline,
        timings       = result.get("timings")
    )


# ==========================================
# Session Routes
# ==========================================

@app.get("/sessions", response_model = list[SessionSummaryOut], tags = ["Sessions"])
def get_my_sessions(current_user: User = Depends(get_current_user)):
    sessions = session_store.list_user_sessions(current_user.id)
    return [SessionSummaryOut(**s.summary()) for s in sessions]


@app.get("/sessions/{session_id}/messages", tags = ["Sessions"])
def get_session_messages(
    session_id   : str,
    db           : Session = Depends(get_db),
    current_user : User    = Depends(get_current_user)
):
    db_session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.user_id    == current_user.id
    ).first()
    if not db_session:
        raise HTTPException(status_code = 404, detail = "Session not found")
    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at).all()
    return [
        {
            "role"        : m.role,
            "content"     : m.content,
            "emotion"     : m.emotion,
            "emotion_conf": m.emotion_conf,
            "language"    : m.language,
            "intent"      : m.intent,
            "crisis_flag" : m.crisis_flag,
            "created_at"  : m.created_at.isoformat()
        }
        for m in messages
    ]


@app.delete("/sessions/{session_id}", tags = ["Sessions"])
def end_session(
    session_id   : str,
    current_user : User = Depends(get_current_user)
):
    session = session_store.get(session_id)
    if session and session.user_id == current_user.id:
        session_store.delete(session_id)
    return {"detail": "Session ended"}


# ==========================================
# Utility Routes
# ==========================================

@app.get("/countries", tags = ["Utility"])
def get_countries():
    return {"countries": list_supported_countries()}


@app.get("/hotline/{country}", tags = ["Utility"])
def get_country_hotline(country: str):
    return get_hotline(country)


@app.get("/health", tags = ["Utility"])
def health():
    return {
        "status"          : "ok",
        "active_sessions" : session_store.active_count()
    }