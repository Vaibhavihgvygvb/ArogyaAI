from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.chat import router as chat_router
from app.api.visit import router as visit_router
from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.doctor import router as doctor_router
from app.api.patient import router as patient_router
from app.api.profile import router as profile_router
from app.api.appointment import router as appointment_router
from app.api.prescription import router as prescription_router
from app.api.prescription_item import router as prescription_item_router
from app.api.medicine import router as medicine_router
from app.api.medical_record import router as medical_record_router
from app.api.notification import router as notification_router
from app.api.search import router as search_router
from app.api.dashboard import router as dashboard_router
from app.database.session import get_db
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered Mental Health Assistant",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(visit_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(doctor_router)
app.include_router(patient_router)
app.include_router(profile_router)
app.include_router(appointment_router)
app.include_router(prescription_router)
app.include_router(prescription_item_router)
app.include_router(medicine_router)
app.include_router(medical_record_router)
app.include_router(notification_router)
app.include_router(search_router)
app.include_router(dashboard_router)


@app.get("/", summary="Root welcome message")
def root():
    return {
        "message": "Welcome to ArogyaAI 🚀"
    }


@app.get("/health", summary="Health check with database status")
def health_check(db: Session = Depends(get_db)):
    db_status = "unhealthy"
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "application": settings.APP_NAME,
        "database": db_status,
        "debug": settings.DEBUG,
    }
