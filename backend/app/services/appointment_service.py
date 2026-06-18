from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, UserRole
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate


CONFLICT_STATUSES = {
    AppointmentStatus.SCHEDULED,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.CHECKED_IN,
    AppointmentStatus.IN_PROGRESS,
}

VALID_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.SCHEDULED: {AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED},
    AppointmentStatus.CONFIRMED: {AppointmentStatus.CHECKED_IN, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW},
    AppointmentStatus.CHECKED_IN: {AppointmentStatus.IN_PROGRESS, AppointmentStatus.CANCELLED},
    AppointmentStatus.IN_PROGRESS: {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED},
    AppointmentStatus.COMPLETED: set(),
    AppointmentStatus.CANCELLED: set(),
    AppointmentStatus.NO_SHOW: set(),
}


class AppointmentValidationError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        self.status_code = status_code
        super().__init__(message)


class AppointmentService:

    @staticmethod
    def _validate_past_appointment(
        appointment_date: date, appointment_time: time
    ) -> None:
        appointment_datetime = datetime.combine(appointment_date, appointment_time)
        if appointment_datetime <= datetime.now():
            raise AppointmentValidationError(
                "Cannot book appointments in the past", status_code=400
            )

    @staticmethod
    def _validate_double_booking(
        db: Session,
        doctor_id: int,
        patient_id: int,
        appointment_date: date,
        appointment_time: time,
        exclude_appointment_id: int | None = None,
    ) -> None:
        stmt = select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.appointment_time == appointment_time,
            Appointment.status.in_(CONFLICT_STATUSES),
        )
        if exclude_appointment_id is not None:
            stmt = stmt.where(Appointment.id != exclude_appointment_id)

        existing = db.scalar(stmt)
        if existing is not None:
            if existing.patient_id == patient_id:
                raise AppointmentValidationError(
                    "Patient already has an appointment with this doctor at this time",
                    status_code=409,
                )
            raise AppointmentValidationError(
                "Doctor already has an appointment at this time",
                status_code=409,
            )

    @staticmethod
    def _validate_completed(appointment: Appointment) -> None:
        if appointment.status == AppointmentStatus.COMPLETED:
            raise AppointmentValidationError(
                "Completed appointments cannot be modified", status_code=409
            )

    @staticmethod
    def _validate_status_transition(
        current_status: AppointmentStatus, new_status: AppointmentStatus
    ) -> None:
        if new_status == current_status:
            return
        if new_status not in VALID_TRANSITIONS[current_status]:
            raise AppointmentValidationError(
                f"Cannot transition from {current_status.value} to {new_status.value}",
                status_code=409,
            )

    @staticmethod
    def _validate_patient_cancel(appointment: Appointment) -> None:
        appt_datetime = datetime.combine(
            appointment.appointment_date, appointment.appointment_time
        )
        if appt_datetime <= datetime.now():
            raise AppointmentValidationError(
                "Patients can only cancel appointments before they begin",
                status_code=400,
            )

    @staticmethod
    def create_appointment(db: Session, appointment_data: AppointmentCreate) -> Appointment:
        AppointmentService._validate_past_appointment(
            appointment_data.appointment_date, appointment_data.appointment_time
        )
        AppointmentService._validate_double_booking(
            db,
            appointment_data.doctor_id,
            appointment_data.patient_id,
            appointment_data.appointment_date,
            appointment_data.appointment_time,
        )
        appointment = Appointment(**appointment_data.model_dump())
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        return appointment

    @staticmethod
    def get_appointment_by_id(db: Session, appointment_id: int) -> Appointment | None:
        return db.get(Appointment, appointment_id)

    @staticmethod
    def get_all_appointments(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        user_role: UserRole | None = None,
        user_doctor_id: int | None = None,
        user_patient_id: int | None = None,
    ) -> list[Appointment]:
        stmt = select(Appointment)
        if user_role == UserRole.DOCTOR and user_doctor_id:
            stmt = stmt.where(Appointment.doctor_id == user_doctor_id)
        elif user_role == UserRole.PATIENT and user_patient_id:
            stmt = stmt.where(Appointment.patient_id == user_patient_id)
        stmt = stmt.offset(skip).limit(limit)
        return list(db.scalars(stmt).all())

    @staticmethod
    def update_appointment(
        db: Session,
        appointment_id: int,
        appointment_update: AppointmentUpdate,
        requesting_user_role: UserRole | None = None,
    ) -> Appointment | None:
        appointment = db.get(Appointment, appointment_id)
        if not appointment:
            return None

        update_data = appointment_update.model_dump(exclude_unset=True)
        if not update_data:
            return appointment

        AppointmentService._validate_completed(appointment)

        if "status" in update_data:
            AppointmentService._validate_status_transition(
                appointment.status, update_data["status"]
            )
            if (
                requesting_user_role == UserRole.PATIENT
                and update_data["status"] == AppointmentStatus.CANCELLED
            ):
                AppointmentService._validate_patient_cancel(appointment)

        check_conflicts = any(
            k in update_data
            for k in ("doctor_id", "patient_id", "appointment_date", "appointment_time")
        )
        if check_conflicts:
            doctor_id = update_data.get("doctor_id", appointment.doctor_id)
            patient_id = update_data.get("patient_id", appointment.patient_id)
            appt_date = update_data.get("appointment_date", appointment.appointment_date)
            appt_time = update_data.get("appointment_time", appointment.appointment_time)

            AppointmentService._validate_past_appointment(appt_date, appt_time)
            AppointmentService._validate_double_booking(
                db, doctor_id, patient_id, appt_date, appt_time,
                exclude_appointment_id=appointment_id,
            )

        for key, value in update_data.items():
            setattr(appointment, key, value)
        db.commit()
        db.refresh(appointment)
        return appointment

    @staticmethod
    def cancel_appointment(
        db: Session,
        appointment_id: int,
        requesting_user_role: UserRole | None = None,
    ) -> Appointment | None:
        return AppointmentService.update_appointment(
            db, appointment_id,
            AppointmentUpdate(status=AppointmentStatus.CANCELLED),
            requesting_user_role=requesting_user_role,
        )

    @staticmethod
    def reschedule_appointment(
        db: Session,
        appointment_id: int,
        new_date: date,
        new_time: time,
        requesting_user_role: UserRole | None = None,
    ) -> Appointment | None:
        return AppointmentService.update_appointment(
            db, appointment_id,
            AppointmentUpdate(appointment_date=new_date, appointment_time=new_time),
            requesting_user_role=requesting_user_role,
        )

    @staticmethod
    def delete_appointment(db: Session, appointment_id: int) -> Appointment | None:
        appointment = db.get(Appointment, appointment_id)
        if not appointment:
            return None
        AppointmentService._validate_completed(appointment)
        db.delete(appointment)
        db.commit()
        return appointment
