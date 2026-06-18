from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.doctor import DoctorUpdate, DoctorResponse
from app.services.doctor_service import DoctorService
from app.api.deps import get_current_user

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get(
    "/me",
    response_model=DoctorResponse,
    summary="Get current doctor profile",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Doctor profile not found"},
    },
)
def get_my_doctor_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctor = DoctorService.get_doctor_by_user_id(db, current_user.id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")
    return doctor


@router.patch(
    "/me",
    response_model=DoctorResponse,
    summary="Update current doctor profile",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Doctor profile not found"},
    },
)
def update_my_doctor_profile(
    update_data: DoctorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctor = DoctorService.get_doctor_by_user_id(db, current_user.id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")
    return DoctorService.update_doctor(db, doctor, update_data)
