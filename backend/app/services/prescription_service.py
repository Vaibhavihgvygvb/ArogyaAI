from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prescription import Prescription
from app.models.visit import Visit
from app.models.enums import UserRole
from app.schemas.prescription import PrescriptionCreate, PrescriptionUpdate


class PrescriptionValidationError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        self.status_code = status_code
        super().__init__(message)


class PrescriptionService:

    @staticmethod
    def _validate_visit_cancelled(visit: Visit) -> None:
        if visit.status and visit.status.lower() == "cancelled":
            raise PrescriptionValidationError(
                "Cannot create prescriptions for cancelled visits", status_code=400
            )

    @staticmethod
    def create_prescription(
        db: Session, prescription_data: PrescriptionCreate
    ) -> Prescription:
        visit = db.get(Visit, prescription_data.visit_id)
        if not visit:
            raise PrescriptionValidationError("Visit not found", status_code=404)

        PrescriptionService._validate_visit_cancelled(visit)

        prescription = Prescription(**prescription_data.model_dump())
        db.add(prescription)
        db.commit()
        db.refresh(prescription)
        return prescription

    @staticmethod
    def get_prescription_by_id(db: Session, prescription_id: int) -> Prescription | None:
        return db.get(Prescription, prescription_id)

    @staticmethod
    def get_all_prescriptions(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        user_role: UserRole | None = None,
        user_doctor_id: int | None = None,
        user_patient_id: int | None = None,
    ) -> list[Prescription]:
        stmt = select(Prescription)
        if user_role == UserRole.DOCTOR and user_doctor_id:
            stmt = stmt.where(Prescription.doctor_id == user_doctor_id)
        elif user_role == UserRole.PATIENT and user_patient_id:
            stmt = stmt.where(Prescription.patient_id == user_patient_id)
        stmt = stmt.offset(skip).limit(limit)
        return list(db.scalars(stmt).all())

    @staticmethod
    def update_prescription(
        db: Session, prescription_id: int, prescription_update: PrescriptionUpdate
    ) -> Prescription | None:
        prescription = db.get(Prescription, prescription_id)
        if not prescription:
            return None
        update_data = prescription_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(prescription, key, value)
        db.commit()
        db.refresh(prescription)
        return prescription

    @staticmethod
    def delete_prescription(db: Session, prescription_id: int) -> Prescription | None:
        prescription = db.get(Prescription, prescription_id)
        if not prescription:
            return None
        db.delete(prescription)
        db.commit()
        return prescription
