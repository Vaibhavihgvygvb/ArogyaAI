from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SearchResultItem(BaseModel):
    entity_type: str
    entity_id: int
    title: str
    subtitle: str | None = None
    summary: str | None = None
    created_at: datetime | None = None
    metadata_json: dict | None = None
    highlight: str | None = None


class SearchResponse(BaseModel):
    items: list[SearchResultItem]
    total: int
    page: int
    page_size: int
    query: str


SEARCHABLE_ENTITY_TYPES = {
    "users", "doctors", "patients", "visits", "appointments",
    "prescriptions", "prescription_items", "medicines",
    "medical_records", "notifications", "audit_logs",
}
