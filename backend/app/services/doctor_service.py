from sqlalchemy.orm import Session
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.doctor import DoctorUpdate
from app.schemas.profile import ProfileCompleteRequest


class DoctorService:

    @staticmethod
    def get_doctor_by_user_id(db: Session, user_id: int) -> Doctor | None:
        return db.query(Doctor).filter(Doctor.user_id == user_id).first()

    @staticmethod
    def update_doctor(db: Session, doctor: Doctor, update_data: DoctorUpdate) -> Doctor:
        data = update_data.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(doctor, key, value)
        db.commit()
        db.refresh(doctor)
        return doctor

    @staticmethod
    def create_doctor_profile(db: Session, user: User, data: ProfileCompleteRequest) -> Doctor:
        doctor = Doctor(
            user_id=user.id,
            full_name=data.full_name,
            email=user.email,
            phone_number=data.phone_number,
            specialization=data.specialization,
            clinic_name=data.clinic_name,
        )
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
        return doctor
