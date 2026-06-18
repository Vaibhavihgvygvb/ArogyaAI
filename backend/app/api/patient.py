from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.patient import PatientUpdate, PatientResponse
from app.services.patient_service import PatientService
from app.api.deps import get_current_user

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get(
    "/me",
    response_model=PatientResponse,
    summary="Get current patient profile",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Patient profile not found"},
    },
)
def get_my_patient_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = PatientService.get_patient_by_user_id(db, current_user.id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    return patient


@router.patch(
    "/me",
    response_model=PatientResponse,
    summary="Update current patient profile",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Patient profile not found"},
    },
)
def update_my_patient_profile(
    update_data: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = PatientService.get_patient_by_user_id(db, current_user.id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    return PatientService.update_patient(db, patient, update_data)
