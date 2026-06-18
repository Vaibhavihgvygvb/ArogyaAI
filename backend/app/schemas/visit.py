from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class VisitBase(BaseModel):
    doctor_id: int
    patient_id: int
    visit_date: datetime
    diagnosis: str | None = None
    symptoms: str | None = None
    prescription: dict | None = None
    instructions: str | None = None
    follow_up_date: date | None = None
    status: str | None = None


class VisitCreate(VisitBase):
    pass


class VisitUpdate(BaseModel):
    doctor_id: int | None = None
    patient_id: int | None = None
    visit_date: datetime | None = None
    diagnosis: str | None = None
    symptoms: str | None = None
    prescription: dict | None = None
    instructions: str | None = None
    follow_up_date: date | None = None
    status: str | None = None


class VisitResponse(VisitBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
