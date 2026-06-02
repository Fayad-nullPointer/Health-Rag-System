from sqlalchemy import Column, Integer, String
from app.db.base import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

    hashed_password = Column(String, nullable=False)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)

    country = Column(String, nullable=False)

    messages = relationship(
        "ChatMessage",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"