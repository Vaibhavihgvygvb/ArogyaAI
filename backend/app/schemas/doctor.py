from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class DoctorUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    phone_number: str | None = Field(None, max_length=20)
    specialization: str | None = Field(None, max_length=255)
    clinic_name: str | None = Field(None, max_length=255)


class DoctorResponse(BaseModel):
    id: int
    user_id: int | None
    full_name: str
    email: EmailStr
    phone_number: str | None
    specialization: str | None
    clinic_name: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
