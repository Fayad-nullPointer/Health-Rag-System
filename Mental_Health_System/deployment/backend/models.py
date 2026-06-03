from sqlalchemy import (
    create_engine, Column, Integer, String,
    Boolean, DateTime, Text, Float, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key = True, index = True)
    username      = Column(String(50),  unique = True,  nullable = False, index = True)
    email         = Column(String(120), unique = True,  nullable = False, index = True)
    hashed_password = Column(String(256), nullable = False)
    country       = Column(String(60),  nullable = False, default = "Unknown")
    created_at    = Column(DateTime(timezone = True), default = utcnow)
    is_active     = Column(Boolean, default = True)

    sessions      = relationship("ChatSession", back_populates = "user",
                                 cascade = "all, delete-orphan")
    crisis_events = relationship("CrisisEvent", back_populates = "user",
                                 cascade = "all, delete-orphan")



class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id         = Column(Integer, primary_key = True, index = True)
    session_id = Column(String(64), unique = True, nullable = False, index = True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable = False)
    started_at = Column(DateTime(timezone = True), default = utcnow)
    ended_at   = Column(DateTime(timezone = True), nullable = True)
    turn_count = Column(Integer, default = 0)

    user     = relationship("User", back_populates = "sessions")
    messages = relationship("Message", back_populates = "session",
                            cascade = "all, delete-orphan",
                            order_by = "Message.created_at")



class Message(Base):
    __tablename__ = "messages"

    id           = Column(Integer, primary_key = True, index = True)
    session_id   = Column(String(64), ForeignKey("chat_sessions.session_id"),
                          nullable = False)
    role         = Column(String(16), nullable = False)   # user | assistant
    content      = Column(Text, nullable = False)
    emotion      = Column(String(30), nullable = True)
    emotion_conf = Column(Float,      nullable = True)
    language     = Column(String(10), nullable = True)
    intent       = Column(String(50), nullable = True)
    crisis_flag  = Column(Boolean, default = False)
    created_at   = Column(DateTime(timezone = True), default = utcnow)

    session = relationship("ChatSession", back_populates = "messages")



class CrisisEvent(Base):
    __tablename__ = "crisis_events"

    id           = Column(Integer, primary_key = True, index = True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable = False)
    session_id   = Column(String(64), nullable = False)
    trigger_text = Column(Text, nullable = False)
    detected_at  = Column(DateTime(timezone = True), default = utcnow)
    resolved     = Column(Boolean, default = False)

    user = relationship("User", back_populates = "crisis_events")




# Database setup
DATABASE_URL = "sqlite:///./mental_health.db"

engine = create_engine(
    DATABASE_URL,
    connect_args = {"check_same_thread": False}   # SQLite only
)


def create_tables():
    Base.metadata.create_all(bind = engine)
