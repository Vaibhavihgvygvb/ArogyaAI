from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.enums import UserRole
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.visit import VisitCreate, VisitUpdate, VisitResponse
from app.services.visit_service import VisitService
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/visits", tags=["Visits"])


@router.post(
    "",
    response_model=VisitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new visit",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Doctor or Admin access required"},
    },
)
def create_visit(
    visit_data: VisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
):
    return VisitService.create_visit(db, visit_data)


@router.get(
    "",
    response_model=list[VisitResponse],
    summary="List visits",
    description="Returns visits filtered by role. Doctors see their own patients' visits. Patients see their own visits.",
)
def get_all_visits(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctor_id = None
    patient_id = None
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if doctor:
            doctor_id = doctor.id
    elif current_user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if patient:
            patient_id = patient.id
    return VisitService.get_all_visits(
        db,
        skip=skip,
        limit=limit,
        user_role=current_user.role,
        user_doctor_id=doctor_id,
        user_patient_id=patient_id,
    )


@router.get(
    "/{visit_id}",
    response_model=VisitResponse,
    summary="Get a visit by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Visit not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def get_visit_by_id(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    visit = VisitService.get_visit_by_id(db, visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or visit.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif current_user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or visit.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return visit


@router.put(
    "/{visit_id}",
    response_model=VisitResponse,
    summary="Update a visit",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Visit not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def update_visit(
    visit_id: int,
    visit_update: VisitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
):
    visit = VisitService.get_visit_by_id(db, visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or visit.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return VisitService.update_visit(db, visit_id, visit_update)


@router.delete(
    "/{visit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a visit",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Visit not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def delete_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
):
    visit = VisitService.get_visit_by_id(db, visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or visit.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    VisitService.delete_visit(db, visit_id)
