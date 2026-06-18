from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

VALID_DOSAGE_FORMS = {
    "Tablet", "Capsule", "Syrup", "Injection", "Cream", "Ointment",
    "Drops", "Inhaler", "Spray", "Patch", "Suppository", "Lotion",
    "Gel", "Powder", "Solution", "Suspension", "Elixir", "Lozenge",
}

VALID_ROUTES = {
    "Oral", "Topical", "Intravenous", "Intramuscular", "Subcutaneous",
    "Inhalation", "Sublingual", "Rectal", "Vaginal", "Ophthalmic",
    "Otic", "Nasal", "Buccal", "Transdermal",
}


class MedicineBase(BaseModel):
    generic_name: str = Field(min_length=1, max_length=255)
    brand_name: str = Field(min_length=1, max_length=255)
    manufacturer: str | None = Field(max_length=255, default=None)
    strength: str = Field(min_length=1, max_length=100)
    dosage_form: str = Field(min_length=1, max_length=100)
    route: str = Field(min_length=1, max_length=100)
    drug_class: str | None = Field(max_length=255, default=None)
    requires_prescription: bool = True
    contraindications: str | None = None
    side_effects: str | None = None
    drug_interactions: str | None = None
    pregnancy_category: str | None = Field(max_length=10, default=None)
    storage_information: str | None = None
    description: str | None = None
    is_active: bool = True


class MedicineCreate(MedicineBase):
    pass


class MedicineUpdate(BaseModel):
    generic_name: str | None = Field(min_length=1, max_length=255, default=None)
    brand_name: str | None = Field(min_length=1, max_length=255, default=None)
    manufacturer: str | None = Field(max_length=255, default=None)
    strength: str | None = Field(min_length=1, max_length=100, default=None)
    dosage_form: str | None = Field(min_length=1, max_length=100, default=None)
    route: str | None = Field(min_length=1, max_length=100, default=None)
    drug_class: str | None = Field(max_length=255, default=None)
    requires_prescription: bool | None = None
    contraindications: str | None = None
    side_effects: str | None = None
    drug_interactions: str | None = None
    pregnancy_category: str | None = Field(max_length=10, default=None)
    storage_information: str | None = None
    description: str | None = None
    is_active: bool | None = None


class MedicineResponse(MedicineBase):
    id: int
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
