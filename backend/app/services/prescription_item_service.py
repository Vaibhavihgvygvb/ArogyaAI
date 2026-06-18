from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prescription import Prescription
from app.models.prescription_item import PrescriptionItem
from app.models.enums import UserRole
from app.schemas.prescription_item import PrescriptionItemCreate, PrescriptionItemUpdate


class PrescriptionItemValidationError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        self.status_code = status_code
        super().__init__(message)


class PrescriptionItemService:

    @staticmethod
    def _validate_prescription_exists(db: Session, prescription_id: int) -> Prescription:
        prescription = db.get(Prescription, prescription_id)
        if not prescription:
            raise PrescriptionItemValidationError("Prescription not found", status_code=404)
        return prescription

    @staticmethod
    def _validate_medicine_name(medicine_name: str) -> None:
        if not medicine_name or not medicine_name.strip():
            raise PrescriptionItemValidationError("Medicine name cannot be empty", status_code=400)

    @staticmethod
    def create_item(
        db: Session, prescription_id: int, item_data: PrescriptionItemCreate
    ) -> PrescriptionItem:
        prescription = PrescriptionItemService._validate_prescription_exists(db, prescription_id)
        PrescriptionItemService._validate_medicine_name(item_data.medicine_name)

        item = PrescriptionItem(prescription_id=prescription.id, **item_data.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def get_item(db: Session, item_id: int) -> PrescriptionItem | None:
        return db.get(PrescriptionItem, item_id)

    @staticmethod
    def list_items(
        db: Session,
        prescription_id: int,
        user_role: UserRole | None = None,
        user_doctor_id: int | None = None,
        user_patient_id: int | None = None,
    ) -> list[PrescriptionItem]:
        prescription = PrescriptionItemService._validate_prescription_exists(db, prescription_id)

        stmt = select(PrescriptionItem).where(
            PrescriptionItem.prescription_id == prescription.id
        )

        if user_role == UserRole.DOCTOR and user_doctor_id:
            stmt = stmt.join(Prescription).where(Prescription.doctor_id == user_doctor_id)
        elif user_role == UserRole.PATIENT and user_patient_id:
            stmt = stmt.join(Prescription).where(Prescription.patient_id == user_patient_id)

        return list(db.scalars(stmt).all())

    @staticmethod
    def update_item(
        db: Session, item_id: int, item_update: PrescriptionItemUpdate
    ) -> PrescriptionItem | None:
        item = db.get(PrescriptionItem, item_id)
        if not item:
            return None

        update_data = item_update.model_dump(exclude_unset=True)

        if "medicine_name" in update_data:
            PrescriptionItemService._validate_medicine_name(update_data["medicine_name"])

        for key, value in update_data.items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def delete_item(db: Session, item_id: int) -> PrescriptionItem | None:
        item = db.get(PrescriptionItem, item_id)
        if not item:
            return None
        db.delete(item)
        db.commit()
        return item
