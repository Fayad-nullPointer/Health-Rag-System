"""
Authentication module – JWT tokens backed by a local SQLite user store.

Provides user registration, login, token creation, and a FastAPI
dependency (`get_current_user`) for protecting endpoints.
"""

import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS

logger = logging.getLogger(__name__)

# ── Password hashing ──────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── OAuth2 scheme (points to login endpoint) ──────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

# ── SQLite helpers ─────────────────────────────────────────────────────────
DB_PATH = "users.db"
BCRYPT_PASSWORD_MAX_BYTES = 72


def _truncate_password(password: str) -> str:
    """Truncate the password to bcrypt's 72-byte limit using UTF-8 encoding."""
    encoded = password.encode("utf-8")[:BCRYPT_PASSWORD_MAX_BYTES]
    return encoded.decode("utf-8", errors="ignore")


def _get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with row-factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the users table if it does not already exist."""
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    logger.info("Auth DB initialised (path=%s)", DB_PATH)


# ── User CRUD ──────────────────────────────────────────────────────────────


def create_user(username: str, password: str) -> dict:
    """Register a new user.

    Returns:
        A dict with the user's ``id`` and ``username``.

    Raises:
        ValueError: If a user with the same username already exists.
    """
    truncated_password = _truncate_password(password)
    hashed = pwd_context.hash(truncated_password)
    try:
        with _get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hashed),
            )
            conn.commit()
            return {"id": cursor.lastrowid, "username": username}
    except sqlite3.IntegrityError:
        raise ValueError(f"Username '{username}' already exists")


def authenticate_user(username: str, password: str) -> Optional[str]:
    """Verify credentials and return a JWT token, or ``None`` on failure."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()

    if row is None:
        return None
    truncated_password = _truncate_password(password)
    if not pwd_context.verify(truncated_password, row["password_hash"]):
        return None

    return create_access_token({"sub": username})


# ── Token helpers ──────────────────────────────────────────────────────────


def create_access_token(data: dict) -> str:
    """Create a signed JWT with an expiration claim."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """FastAPI dependency – extracts and validates the current user from a Bearer token.

    Returns:
        A dict with at least ``{"username": "<name>"}``.

    Raises:
        HTTPException 401: If the token is missing, expired, or invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return {"username": username}


# ── Auto-init on import ───────────────────────────────────────────────────
init_db()
