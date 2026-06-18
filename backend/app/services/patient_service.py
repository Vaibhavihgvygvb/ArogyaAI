from sqlalchemy.orm import Session
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import PatientUpdate
from app.schemas.profile import ProfileCompleteRequest


class PatientService:

    @staticmethod
    def get_patient_by_user_id(db: Session, user_id: int) -> Patient | None:
        return db.query(Patient).filter(Patient.user_id == user_id).first()

    @staticmethod
    def update_patient(db: Session, patient: Patient, update_data: PatientUpdate) -> Patient:
        data = update_data.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(patient, key, value)
        db.commit()
        db.refresh(patient)
        return patient

    @staticmethod
    def create_patient_profile(db: Session, user: User, data: ProfileCompleteRequest) -> Patient:
        patient = Patient(
            user_id=user.id,
            full_name=data.full_name,
            phone_number=data.phone_number,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            emergency_contact=data.emergency_contact,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient
