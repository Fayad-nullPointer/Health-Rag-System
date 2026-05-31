from fastapi import APIRouter
from pydantic import BaseModel

from app.services.chatbot_service import process_message

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(request: ChatRequest):

    result = process_message(
        request.message
    )

    return result