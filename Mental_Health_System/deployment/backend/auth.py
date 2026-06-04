import os
from datetime import datetime, timedelta, timezone
from typing   import Optional

import bcrypt  # <-- Switched to modern native bcrypt
from fastapi.security  import OAuth2PasswordBearer
from jose              import JWTError, jwt
from pydantic          import BaseModel, EmailStr
from sqlalchemy.orm    import Session

from models import User

# Config
SECRET_KEY        = os.getenv("SECRET_KEY", "change-this-in-production")
ALGORITHM         = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24   # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "/auth/login")


# ==========================================
# Pydantic Schemas
# ==========================================

class RegisterRequest(BaseModel):
    username : str
    email    : EmailStr
    password : str
    country  : str


class LoginRequest(BaseModel):
    email    : EmailStr
    password : str


class TokenResponse(BaseModel):
    access_token : str
    token_type   : str = "bearer"
    username     : str
    country      : str


class UserOut(BaseModel):
    id         : int
    username   : str
    email      : str
    country    : str
    created_at : datetime

    class Config:
        from_attributes = True


# ==========================================
# Password Helpers (Clean Native Byte Hashing)
# ==========================================

def hash_password(password: str) -> str:
    # 1. Convert string to clean UTF-8 bytes
    pwd_bytes = password.encode('utf-8')
    
    # 2. Hard truncate to 72 bytes max to stay within architectural limits
    if len(pwd_bytes) > 72:
        pwd_bytes = pwd_bytes[:72]
        
    # 3. Generate salt and hash natively
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    
    # 4. Return as a clean string to store safely in SQLite text columns
    return hashed_bytes.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        pwd_bytes = plain.encode('utf-8')
        if len(pwd_bytes) > 72:
            pwd_bytes = pwd_bytes[:72]
            
        # Convert stored string hash back to bytes for verification validation
        hashed_bytes = hashed.encode('utf-8')
        
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


# ==========================================
# Token Helpers
# ==========================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire  = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm = ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms = [ALGORITHM])
    except JWTError:
        return None


# ==========================================
# DB Helpers
# ==========================================

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, data: RegisterRequest) -> User:
    user = User(
        username        = data.username.strip(),
        email           = data.email.lower().strip(),
        hashed_password = hash_password(data.password),
        country         = data.country.strip()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ==========================================
# FastAPI Dependencies
# ==========================================
# NOTE: get_current_user is defined in app.py with proper
# Depends(get_db) injection. Do not duplicate it here.