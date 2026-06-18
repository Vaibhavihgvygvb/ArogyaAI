import re
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MedicalRecordCreate(BaseModel):
    visit_id: int
    doctor_id: int
    patient_id: int

    chief_complaint: str | None = None
    history_of_present_illness: str | None = None
    past_medical_history: str | None = None
    family_history: str | None = None
    surgical_history: str | None = None
    allergy_history: str | None = None
    medication_history: str | None = None
    social_history: str | None = None

    physical_examination: str | None = None
    assessment: str | None = None
    diagnosis: str = Field(min_length=1)

    treatment_plan: str | None = None
    follow_up_instructions: str | None = None

    height: float | None = Field(default=None, gt=0)
    weight: float | None = Field(default=None, gt=0)
    bmi: float | None = Field(default=None, ge=0)
    blood_pressure: str | None = Field(max_length=20, default=None)
    pulse: float | None = Field(default=None, ge=0)
    respiratory_rate: float | None = Field(default=None, ge=0)
    temperature: float | None = Field(default=None, ge=34.0, le=43.0)
    oxygen_saturation: float | None = Field(default=None, ge=0, le=100)

    notes: str | None = None

    @field_validator("blood_pressure")
    @classmethod
    def validate_blood_pressure(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^\d{2,3}/\d{2,3}$", v):
            raise ValueError("Blood pressure must be in format '120/80'")
        return v


class MedicalRecordUpdate(BaseModel):
    visit_id: int | None = None
    chief_complaint: str | None = None
    history_of_present_illness: str | None = None
    past_medical_history: str | None = None
    family_history: str | None = None
    surgical_history: str | None = None
    allergy_history: str | None = None
    medication_history: str | None = None
    social_history: str | None = None

    physical_examination: str | None = None
    assessment: str | None = None
    diagnosis: str | None = Field(min_length=1, default=None)

    treatment_plan: str | None = None
    follow_up_instructions: str | None = None

    height: float | None = Field(default=None, gt=0)
    weight: float | None = Field(default=None, gt=0)
    bmi: float | None = Field(default=None, ge=0)
    blood_pressure: str | None = Field(max_length=20, default=None)
    pulse: float | None = Field(default=None, ge=0)
    respiratory_rate: float | None = Field(default=None, ge=0)
    temperature: float | None = Field(default=None, ge=34.0, le=43.0)
    oxygen_saturation: float | None = Field(default=None, ge=0, le=100)

    notes: str | None = None

    @field_validator("blood_pressure")
    @classmethod
    def validate_blood_pressure(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^\d{2,3}/\d{2,3}$", v):
            raise ValueError("Blood pressure must be in format '120/80'")
        return v


class MedicalRecordResponse(BaseModel):
    id: int
    visit_id: int
    doctor_id: int
    patient_id: int

    chief_complaint: str | None
    history_of_present_illness: str | None
    past_medical_history: str | None
    family_history: str | None
    surgical_history: str | None
    allergy_history: str | None
    medication_history: str | None
    social_history: str | None

    physical_examination: str | None
    assessment: str | None
    diagnosis: str

    treatment_plan: str | None
    follow_up_instructions: str | None

    height: float | None
    weight: float | None
    bmi: float | None
    blood_pressure: str | None
    pulse: float | None
    respiratory_rate: float | None
    temperature: float | None
    oxygen_saturation: float | None

    notes: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
