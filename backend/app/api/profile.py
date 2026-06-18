from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.profile import ProfileCompleteRequest
from app.services.doctor_service import DoctorService
from app.services.patient_service import PatientService
from app.api.deps import get_current_user

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.post(
    "/complete",
    summary="Complete user profile based on role",
    description="Creates a Doctor or Patient profile for the authenticated user. Role is determined from JWT. Returns 409 if profile already exists.",
    responses={
        status.HTTP_409_CONFLICT: {"description": "Profile already completed"},
        status.HTTP_400_BAD_REQUEST: {"description": "Profile completion not supported for this role"},
    },
)
def complete_profile(
    request: ProfileCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.DOCTOR:
        if DoctorService.get_doctor_by_user_id(db, current_user.id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already completed")
        return DoctorService.create_doctor_profile(db, current_user, request)

    if current_user.role == UserRole.PATIENT:
        if PatientService.get_patient_by_user_id(db, current_user.id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already completed")
        return PatientService.create_patient_profile(db, current_user, request)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Profile completion not supported for this role",
    )
