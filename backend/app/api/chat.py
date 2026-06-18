from fastapi import APIRouter
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["Chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a chat message",
    description="Stub endpoint that echoes the user message. Intended for future AI integration.",
)
def chat(request: ChatRequest):
    return ChatResponse(
        response=f"You said: {request.message}"
    )