from fastapi import APIRouter
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    return ChatResponse(
        response=f"You said: {request.message}"
    )