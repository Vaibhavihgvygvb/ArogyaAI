from fastapi import FastAPI
from app.api.chat import router as chat_router
from app.database.base import Base
from app.database.session import engine
import app.models

app = FastAPI(
    title="ArogyaAI",
    description="AI-powered Mental Health Assistant",
    version="1.0.0"
)

app.include_router(chat_router)

@app.on_event("startup")
async def startup_event():
    # Import all models here before create_all to ensure they are registered with Base
    Base.metadata.create_all(bind=engine)

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
