"""
Authentication routes – user registration and login.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

import auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["auth"])


# ── Request / Response schemas ─────────────────────────────────────────────


class AuthRequest(BaseModel):
    """Body for register and login endpoints."""

    username: str
    password: str


class AuthResponse(BaseModel):
    """Returned on successful authentication."""

    token: str
    username: str


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def register(body: AuthRequest):
    """Register a new user and return a JWT token."""
    logger.info("Registration request received for username: %s", body.username)
    try:
        user = auth.create_user(body.username, body.password)
        logger.info("User registered successfully: %s", body.username)
    except ValueError as exc:
        logger.warning("Registration failed for user %s: %s", body.username, str(exc))
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    token = auth.create_access_token({"sub": user["username"]})
    return AuthResponse(token=token, username=user["username"])


@router.post("/login", response_model=AuthResponse)
async def login(body: AuthRequest):
    """Authenticate an existing user and return a JWT token."""
    logger.info("Login request received for username: %s", body.username)
    token = auth.authenticate_user(body.username, body.password)
    if token is None:
        logger.warning("Failed login attempt for username: %s", body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logger.info("Successful login for username: %s", body.username)
    return AuthResponse(token=token, username=body.username)
