from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from fastapi import Header, HTTPException

SECRET_KEY = "super-secret-key"
ALGORITHM = "HS256"

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_minutes=60 * 24 * 7):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user_id(
    authorization: str = Header(None)
):

    print("AUTH HEADER:", authorization)

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    token = authorization.replace("Bearer ", "")

    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM]
    )

    return payload["user_id"]