from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password, verify_password

def create_user(db: Session, username, email, password, country):
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        country=country
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str):
    print("Login attempt:", username)

    user = db.query(User).filter(User.username == username).first()

    print("User found:", user)

    if not user:
        return None

    print("Stored hash:", user.hashed_password)

    try:
        result = verify_password(password, user.hashed_password)
        print("Password match:", result)
    except Exception as e:
        print("Verify error:", str(e))
        return None

    if not result:
        return None

    return user