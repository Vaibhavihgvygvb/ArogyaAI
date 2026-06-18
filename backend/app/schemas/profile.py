from datetime import date
from pydantic import BaseModel, Field


class ProfileCompleteRequest(BaseModel):
    full_name: str = Field(max_length=255)
    phone_number: str = Field(max_length=20)
    specialization: str | None = Field(None, max_length=255)
    clinic_name: str | None = Field(None, max_length=255)
    date_of_birth: date | None = None
    gender: str | None = Field(None, max_length=20)
    emergency_contact: str | None = Field(None, max_length=20)
