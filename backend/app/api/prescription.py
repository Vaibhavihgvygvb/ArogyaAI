from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.enums import UserRole
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.prescription import PrescriptionCreate, PrescriptionUpdate, PrescriptionResponse
from app.services.prescription_service import PrescriptionService, PrescriptionValidationError
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


@router.post(
    "",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new prescription",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Visit cancelled or invalid"},
        status.HTTP_403_FORBIDDEN: {"description": "Doctor or Admin access required"},
        status.HTTP_404_NOT_FOUND: {"description": "Visit not found"},
    },
)
def create_prescription(
    prescription_data: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
):
    try:
        return PrescriptionService.create_prescription(db, prescription_data)
    except PrescriptionValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(
    "",
    response_model=list[PrescriptionResponse],
    summary="List prescriptions",
    description="Returns prescriptions filtered by role. Doctors see their own. Patients see their own.",
)
def get_all_prescriptions(
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
    return PrescriptionService.get_all_prescriptions(
        db,
        skip=skip,
        limit=limit,
        user_role=current_user.role,
        user_doctor_id=doctor_id,
        user_patient_id=patient_id,
    )


@router.get(
    "/{prescription_id}",
    response_model=PrescriptionResponse,
    summary="Get a prescription by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Prescription not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def get_prescription_by_id(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prescription = PrescriptionService.get_prescription_by_id(db, prescription_id)
    if not prescription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or prescription.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif current_user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or prescription.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return prescription


@router.patch(
    "/{prescription_id}",
    response_model=PrescriptionResponse,
    summary="Update a prescription",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Prescription not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def update_prescription(
    prescription_id: int,
    prescription_update: PrescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
):
    prescription = PrescriptionService.get_prescription_by_id(db, prescription_id)
    if not prescription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or prescription.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return PrescriptionService.update_prescription(db, prescription_id, prescription_update)


@router.delete(
    "/{prescription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a prescription",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Prescription not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def delete_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
):
    prescription = PrescriptionService.get_prescription_by_id(db, prescription_id)
    if not prescription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or prescription.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    PrescriptionService.delete_prescription(db, prescription_id)
