from fastapi import FastAPI
from app.api.chat import router as chat_router

app = FastAPI(
    title="ArogyaAI",
    description="AI-powered Mental Health Assistant",
    version="1.0.0"
)

app.include_router(chat_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to ArogyaAI 🚀"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }