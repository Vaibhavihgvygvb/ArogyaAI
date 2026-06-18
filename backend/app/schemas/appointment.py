from datetime import date, time, datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AppointmentStatus


class AppointmentBase(BaseModel):
    doctor_id: int
    patient_id: int
    appointment_date: date
    appointment_time: time
    reason: str = Field(min_length=1, max_length=500)
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    notes: str | None = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    doctor_id: int | None = None
    patient_id: int | None = None
    appointment_date: date | None = None
    appointment_time: time | None = None
    reason: str | None = Field(min_length=1, max_length=500, default=None)
    status: AppointmentStatus | None = None
    notes: str | None = None


class AppointmentResponse(AppointmentBase):
    id: int
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
