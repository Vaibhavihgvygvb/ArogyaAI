from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PrescriptionItemBase(BaseModel):
    medicine_name: str = Field(min_length=1, max_length=255)
    strength: str | None = Field(max_length=100, default=None)
    dosage: str | None = Field(max_length=100, default=None)
    frequency: str | None = Field(max_length=100, default=None)
    duration: str | None = Field(max_length=100, default=None)
    quantity: int | None = None
    route: str | None = Field(max_length=100, default=None)
    instructions: str | None = None


class PrescriptionItemCreate(PrescriptionItemBase):
    pass


class PrescriptionItemUpdate(BaseModel):
    medicine_name: str | None = Field(min_length=1, max_length=255, default=None)
    strength: str | None = Field(max_length=100, default=None)
    dosage: str | None = Field(max_length=100, default=None)
    frequency: str | None = Field(max_length=100, default=None)
    duration: str | None = Field(max_length=100, default=None)
    quantity: int | None = None
    route: str | None = Field(max_length=100, default=None)
    instructions: str | None = None


class PrescriptionItemResponse(PrescriptionItemBase):
    id: int
    prescription_id: int
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
