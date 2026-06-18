import json
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.medical_record import MedicalRecord
from app.models.visit import Visit
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordUpdate


MEDICAL_RECORD_FIELDS = {
    "visit_id", "doctor_id", "patient_id",
    "chief_complaint", "history_of_present_illness",
    "past_medical_history", "family_history", "surgical_history",
    "allergy_history", "medication_history", "social_history",
    "physical_examination", "assessment", "diagnosis",
    "treatment_plan", "follow_up_instructions",
    "height", "weight", "bmi", "blood_pressure",
    "pulse", "respiratory_rate", "temperature", "oxygen_saturation",
    "notes",
}


class MedicalRecordValidationError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        self.status_code = status_code
        super().__init__(message)


class MedicalRecordService:

    @staticmethod
    def _validate_visit_exists(db: Session, visit_id: int) -> Visit:
        visit = db.get(Visit, visit_id)
        if not visit:
            raise MedicalRecordValidationError("Visit not found", status_code=404)
        return visit

    @staticmethod
    def _validate_visit_not_cancelled(visit: Visit) -> None:
        if visit.status and visit.status.lower() == "cancelled":
            raise MedicalRecordValidationError(
                "Cannot create medical records for cancelled visits", status_code=400
            )

    @staticmethod
    def _validate_no_duplicate_record(db: Session, visit_id: int) -> None:
        existing = db.scalar(
            select(MedicalRecord).where(MedicalRecord.visit_id == visit_id)
        )
        if existing:
            raise MedicalRecordValidationError(
                "Medical record already exists for this visit", status_code=409
            )

    @staticmethod
    def _validate_doctor_exists(db: Session, doctor_id: int) -> Doctor:
        doctor = db.get(Doctor, doctor_id)
        if not doctor:
            raise MedicalRecordValidationError("Doctor not found", status_code=404)
        return doctor

    @staticmethod
    def _validate_patient_exists(db: Session, patient_id: int) -> Patient:
        patient = db.get(Patient, patient_id)
        if not patient:
            raise MedicalRecordValidationError("Patient not found", status_code=404)
        return patient

    @staticmethod
    def _validate_vitals(height: float | None = None, weight: float | None = None, bmi: float | None = None, temperature: float | None = None, oxygen_saturation: float | None = None, blood_pressure: str | None = None) -> None:
        if height is not None and height < 0:
            raise MedicalRecordValidationError("Height must be non-negative", status_code=400)
        if weight is not None and weight < 0:
            raise MedicalRecordValidationError("Weight must be non-negative", status_code=400)
        if bmi is not None and bmi < 0:
            raise MedicalRecordValidationError("BMI must be non-negative", status_code=400)
        if temperature is not None and (temperature < 34.0 or temperature > 43.0):
            raise MedicalRecordValidationError(
                "Temperature must be between 34.0°C and 43.0°C", status_code=400
            )
        if oxygen_saturation is not None and (oxygen_saturation < 0 or oxygen_saturation > 100):
            raise MedicalRecordValidationError(
                "Oxygen saturation must be between 0 and 100", status_code=400
            )
        if blood_pressure is not None and not re.match(r"^\d{2,3}/\d{2,3}$", blood_pressure):
            raise MedicalRecordValidationError(
                "Blood pressure must be in format '120/80'", status_code=400
            )

    @staticmethod
    def _calculate_bmi(height: float | None, weight: float | None) -> float | None:
        if height is None or weight is None:
            return None
        if height <= 0 or weight <= 0:
            raise MedicalRecordValidationError(
                "Height and weight must be positive values", status_code=400
            )
        height_m = height / 100.0
        return round(weight / (height_m * height_m), 2)

    @staticmethod
    def _validate_doctor_owns_visit(visit: Visit, doctor_id: int) -> None:
        if visit.doctor_id != doctor_id:
            raise MedicalRecordValidationError(
                "Doctor does not own this visit", status_code=403
            )

    @staticmethod
    def _build_audit_details(
        action: str,
        record: MedicalRecord,
        old_values: dict | None = None,
        new_values: dict | None = None,
        changed_fields: list[str] | None = None,
    ) -> str:
        details = {
            "action": action,
            "visit_id": record.visit_id,
            "doctor_id": record.doctor_id,
            "patient_id": record.patient_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if old_values is not None:
            details["old_values"] = old_values
        if new_values is not None:
            details["new_values"] = new_values
        if changed_fields is not None:
            details["changed_fields"] = changed_fields
        return json.dumps(details)

    @staticmethod
    def _snapshot_record(record: MedicalRecord) -> dict:
        return {field: getattr(record, field, None) for field in MEDICAL_RECORD_FIELDS}

    @staticmethod
    def _log_audit(
        db: Session,
        user_id: int,
        action: str,
        resource: str,
        details: str | None = None,
    ) -> None:
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            details=details,
        )
        db.add(log)

    @staticmethod
    def create_record(
        db: Session, record_data: MedicalRecordCreate, user_id: int
    ) -> MedicalRecord:
        visit = MedicalRecordService._validate_visit_exists(db, record_data.visit_id)
        MedicalRecordService._validate_visit_not_cancelled(visit)
        MedicalRecordService._validate_no_duplicate_record(db, record_data.visit_id)
        MedicalRecordService._validate_doctor_exists(db, record_data.doctor_id)
        MedicalRecordService._validate_patient_exists(db, record_data.patient_id)
        MedicalRecordService._validate_doctor_owns_visit(visit, record_data.doctor_id)
        MedicalRecordService._validate_vitals(
            height=record_data.height,
            weight=record_data.weight,
            bmi=record_data.bmi,
            temperature=record_data.temperature,
            oxygen_saturation=record_data.oxygen_saturation,
            blood_pressure=record_data.blood_pressure,
        )

        data = record_data.model_dump()
        bmi = MedicalRecordService._calculate_bmi(data.get("height"), data.get("weight"))
        data["bmi"] = bmi

        record = MedicalRecord(**data)
        db.add(record)
        db.flush()

        new_values = MedicalRecordService._snapshot_record(record)
        details = MedicalRecordService._build_audit_details(
            action="CREATE_MEDICAL_RECORD",
            record=record,
            new_values=new_values,
            changed_fields=list(MEDICAL_RECORD_FIELDS),
        )
        MedicalRecordService._log_audit(
            db, user_id=user_id, action="CREATE_MEDICAL_RECORD",
            resource=f"medical_record:{record.id}",
            details=details,
        )

        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_record(db: Session, record_id: int) -> MedicalRecord | None:
        return db.get(MedicalRecord, record_id)

    @staticmethod
    def get_record_by_visit(db: Session, visit_id: int) -> MedicalRecord | None:
        return db.scalar(
            select(MedicalRecord).where(MedicalRecord.visit_id == visit_id)
        )

    @staticmethod
    def list_records(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        user_role: UserRole | None = None,
        user_doctor_id: int | None = None,
        user_patient_id: int | None = None,
    ) -> list[MedicalRecord]:
        stmt = select(MedicalRecord)
        if user_role == UserRole.DOCTOR and user_doctor_id:
            stmt = stmt.where(MedicalRecord.doctor_id == user_doctor_id)
        elif user_role == UserRole.PATIENT and user_patient_id:
            stmt = stmt.where(MedicalRecord.patient_id == user_patient_id)
        stmt = stmt.offset(skip).limit(limit)
        return list(db.scalars(stmt).all())

    @staticmethod
    def update_record(
        db: Session, record_id: int, record_update: MedicalRecordUpdate, user_id: int
    ) -> MedicalRecord | None:
        record = db.get(MedicalRecord, record_id)
        if not record:
            return None

        update_data = record_update.model_dump(exclude_unset=True)

        visit_id = update_data.get("visit_id")
        if visit_id is not None:
            raise MedicalRecordValidationError(
                "Medical record cannot be reassigned to another visit", status_code=400
            )

        MedicalRecordService._validate_vitals(
            height=update_data.get("height"),
            weight=update_data.get("weight"),
            bmi=update_data.get("bmi"),
            temperature=update_data.get("temperature"),
            oxygen_saturation=update_data.get("oxygen_saturation"),
            blood_pressure=update_data.get("blood_pressure"),
        )

        old_values = MedicalRecordService._snapshot_record(record)
        changed_fields = list(update_data.keys())

        if "height" in update_data or "weight" in update_data:
            eff_height = update_data.get("height", record.height)
            eff_weight = update_data.get("weight", record.weight)
            bmi = MedicalRecordService._calculate_bmi(eff_height, eff_weight)
            if bmi is not None:
                update_data["bmi"] = bmi
                if "bmi" not in changed_fields:
                    changed_fields.append("bmi")

        for key, value in update_data.items():
            setattr(record, key, value)

        new_values = MedicalRecordService._snapshot_record(record)
        details = MedicalRecordService._build_audit_details(
            action="UPDATE_MEDICAL_RECORD",
            record=record,
            old_values={k: old_values[k] for k in changed_fields if k in old_values},
            new_values={k: new_values[k] for k in changed_fields if k in new_values},
            changed_fields=changed_fields,
        )
        MedicalRecordService._log_audit(
            db, user_id=user_id, action="UPDATE_MEDICAL_RECORD",
            resource=f"medical_record:{record_id}",
            details=details,
        )

        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def delete_record(db: Session, record_id: int, user_id: int) -> MedicalRecord | None:
        record = db.get(MedicalRecord, record_id)
        if not record:
            return None
        old_values = MedicalRecordService._snapshot_record(record)
        visit_id = record.visit_id
        db.delete(record)

        details = MedicalRecordService._build_audit_details(
            action="DELETE_MEDICAL_RECORD",
            record=record,
            old_values=old_values,
        )
        MedicalRecordService._log_audit(
            db, user_id=user_id, action="DELETE_MEDICAL_RECORD",
            resource=f"medical_record:{record_id}",
            details=details,
        )

        db.commit()
        return record
