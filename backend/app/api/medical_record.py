from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.enums import UserRole
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordUpdate, MedicalRecordResponse
from app.services.medical_record_service import MedicalRecordService, MedicalRecordValidationError
from app.api.deps import get_current_user, require_roles

router = APIRouter(tags=["Medical Records"])


@router.post(
    "/medical-records",
    response_model=MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a medical record for a visit",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Visit cancelled or invalid data"},
        status.HTTP_403_FORBIDDEN: {"description": "Doctor or Admin access required"},
        status.HTTP_404_NOT_FOUND: {"description": "Visit, doctor, or patient not found"},
        status.HTTP_409_CONFLICT: {"description": "Record already exists for this visit"},
    },
)
def create_medical_record(
    record_data: MedicalRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
):
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or doctor.id != record_data.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only create records for yourself as doctor",
            )
    try:
        return MedicalRecordService.create_record(db, record_data, user_id=current_user.id)
    except MedicalRecordValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(
    "/medical-records",
    response_model=list[MedicalRecordResponse],
    summary="List medical records",
    description="Returns records filtered by role. Doctors see their own. Patients see their own.",
)
def list_medical_records(
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
    return MedicalRecordService.list_records(
        db,
        skip=skip,
        limit=limit,
        user_role=current_user.role,
        user_doctor_id=doctor_id,
        user_patient_id=patient_id,
    )


@router.get(
    "/medical-records/{record_id}",
    response_model=MedicalRecordResponse,
    summary="Get a medical record by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Record not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def get_medical_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = MedicalRecordService.get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical record not found")
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or record.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif current_user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or record.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return record


@router.get(
    "/visits/{visit_id}/medical-record",
    response_model=MedicalRecordResponse,
    summary="Get medical record by visit ID",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Record not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def get_medical_record_by_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = MedicalRecordService.get_record_by_visit(db, visit_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical record not found for this visit")
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or record.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif current_user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or record.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return record


@router.patch(
    "/medical-records/{record_id}",
    response_model=MedicalRecordResponse,
    summary="Update a medical record",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Record not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
        status.HTTP_400_BAD_REQUEST: {"description": "Cannot reassign visit or invalid vitals"},
    },
)
def update_medical_record(
    record_id: int,
    record_update: MedicalRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
):
    record = MedicalRecordService.get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical record not found")
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or record.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        return MedicalRecordService.update_record(db, record_id, record_update, user_id=current_user.id)
    except MedicalRecordValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.delete(
    "/medical-records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a medical record",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Record not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required"},
    },
)
def delete_medical_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    record = MedicalRecordService.get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical record not found")
    MedicalRecordService.delete_record(db, record_id, user_id=current_user.id)
