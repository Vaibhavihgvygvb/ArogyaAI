from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class PatientUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    phone_number: str | None = Field(None, max_length=20)
    date_of_birth: date | None = None
    gender: str | None = Field(None, max_length=20)
    emergency_contact: str | None = Field(None, max_length=20)


class PatientResponse(BaseModel):
    id: int
    user_id: int | None
    full_name: str
    phone_number: str
    date_of_birth: date | None
    gender: str | None
    emergency_contact: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
