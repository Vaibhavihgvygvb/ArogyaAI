from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.visit import Visit
from app.models.enums import UserRole
from app.schemas.visit import VisitCreate, VisitUpdate


class VisitService:

    @staticmethod
    def create_visit(db: Session, visit_data: VisitCreate) -> Visit:
        visit = Visit(**visit_data.model_dump())
        db.add(visit)
        db.commit()
        db.refresh(visit)
        return visit

    @staticmethod
    def get_visit_by_id(db: Session, visit_id: int) -> Visit | None:
        return db.get(Visit, visit_id)

    @staticmethod
    def get_all_visits(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        user_role: UserRole | None = None,
        user_doctor_id: int | None = None,
        user_patient_id: int | None = None,
    ) -> list[Visit]:
        stmt = select(Visit)
        if user_role == UserRole.DOCTOR and user_doctor_id:
            stmt = stmt.where(Visit.doctor_id == user_doctor_id)
        elif user_role == UserRole.PATIENT and user_patient_id:
            stmt = stmt.where(Visit.patient_id == user_patient_id)
        stmt = stmt.offset(skip).limit(limit)
        return list(db.scalars(stmt).all())

    @staticmethod
    def update_visit(db: Session, visit_id: int, visit_update: VisitUpdate) -> Visit | None:
        visit = db.get(Visit, visit_id)
        if not visit:
            return None
        update_data = visit_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(visit, key, value)
        db.commit()
        db.refresh(visit)
        return visit

    @staticmethod
    def delete_visit(db: Session, visit_id: int) -> Visit | None:
        visit = db.get(Visit, visit_id)
        if not visit:
            return None
        db.delete(visit)
        db.commit()
        return visit
