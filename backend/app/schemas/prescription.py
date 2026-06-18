from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PrescriptionBase(BaseModel):
    visit_id: int
    doctor_id: int
    patient_id: int
    diagnosis: str = Field(min_length=1, max_length=5000)
    notes: str | None = None


class PrescriptionCreate(PrescriptionBase):
    pass


class PrescriptionUpdate(BaseModel):
    diagnosis: str | None = Field(min_length=1, max_length=5000, default=None)
    notes: str | None = None


class PrescriptionResponse(PrescriptionBase):
    id: int
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
