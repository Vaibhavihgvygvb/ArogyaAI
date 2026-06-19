from enum import Enum
from pydantic import BaseModel, Field


class TerminologySystem(str, Enum):
    ICD_10 = "icd_10"
    ICD_11 = "icd_11"
    SNOMED_CT = "snomed_ct"
    LOINC = "loinc"
    RXNORM = "rxnorm"
    ATC = "atc"


class TaxonomyMapping(BaseModel):
    source_term: str = ""
    source_system: TerminologySystem | None = None
    target_code: str | None = None
    target_display: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    mapping_system: str = ""


class TaxonomyResult(BaseModel):
    term: str
    mappings: list[TaxonomyMapping] = Field(default_factory=list)
    available_systems: list[TerminologySystem] = Field(default_factory=list)
    total_mappings: int = 0
