from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse

from app.schemas.user import UserCreate, UserLogin
from app.services.auth_service import create_user, authenticate_user
from app.core.security import create_access_token
from app.core.database import SessionLocal


router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    new_user = create_user(
        db,
        username=user.username,
        email=user.email,
        password=user.password,
        country=user.country,
        first_name=user.first_name,
        last_name=user.last_name
    )

    return {"message": "User created", "user_id": new_user.id}


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    print("LOGIN ENDPOINT CALLED")

    db_user = authenticate_user(db, user.username, user.password)

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"user_id": db_user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": db_user.username,
        "full_name": db_user.full_name
    }




@router.post("/logout")
def logout():
    response = JSONResponse(
        content={"message": "Logged out successfully"}
    )

    response.delete_cookie("access_token")

    return response