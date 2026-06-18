from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.enums import AppointmentStatus, UserRole
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate, AppointmentResponse
from app.services.appointment_service import AppointmentService, AppointmentValidationError
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new appointment",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Appointment in the past"},
        status.HTTP_403_FORBIDDEN: {"description": "Doctor, Patient, or Admin access required"},
        status.HTTP_409_CONFLICT: {"description": "Time slot conflict"},
    },
)
def create_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.PATIENT, UserRole.ADMIN)),
):
    try:
        return AppointmentService.create_appointment(db, appointment_data)
    except AppointmentValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(
    "",
    response_model=list[AppointmentResponse],
    summary="List appointments",
    description="Returns appointments filtered by role. Doctors see their own appointments. Patients see their own.",
)
def get_all_appointments(
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
    return AppointmentService.get_all_appointments(
        db,
        skip=skip,
        limit=limit,
        user_role=current_user.role,
        user_doctor_id=doctor_id,
        user_patient_id=patient_id,
    )


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Get an appointment by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Appointment not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def get_appointment_by_id(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = AppointmentService.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or appointment.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif current_user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or appointment.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return appointment


@router.patch(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Update an appointment",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Appointment not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
        status.HTTP_409_CONFLICT: {"description": "Validation conflict"},
    },
)
def update_appointment(
    appointment_id: int,
    appointment_update: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = AppointmentService.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    if current_user.role == UserRole.ADMIN:
        pass
    elif current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or appointment.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif current_user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or appointment.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        update_data = appointment_update.model_dump(exclude_unset=True)
        if set(update_data.keys()) != {"status"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only cancel their own appointments",
            )
        if update_data.get("status") != AppointmentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only cancel their own appointments",
            )
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        return AppointmentService.update_appointment(
            db, appointment_id, appointment_update,
            requesting_user_role=current_user.role,
        )
    except AppointmentValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.delete(
    "/{appointment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an appointment",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Appointment not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
        status.HTTP_409_CONFLICT: {"description": "Completed appointments cannot be deleted"},
    },
)
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
):
    appointment = AppointmentService.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or appointment.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        AppointmentService.delete_appointment(db, appointment_id)
    except AppointmentValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
