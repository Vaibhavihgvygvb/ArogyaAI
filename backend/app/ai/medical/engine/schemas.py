from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class AnalysisScope(str, Enum):
    INTENT = "intent"
    ENTITIES = "entities"
    SPECIALTY = "specialty"
    URGENCY = "urgency"
    AUDIENCE = "audience"
    LANGUAGE = "language"
    REWRITE = "rewrite"
    FULL = "full"


class EntityType(str, Enum):
    SYMPTOM = "symptom"
    DISEASE = "disease"
    MEDICATION = "medication"
    PROCEDURE = "procedure"
    LAB_TEST = "lab_test"
    VITAL_SIGN = "vital_sign"
    ANATOMY = "anatomy"
    ALLERGY = "allergy"
    DOSAGE = "dosage"
    TIME_EXPRESSION = "time_expression"
    AGE_REFERENCE = "age_reference"
    CHRONIC_CONDITION = "chronic_condition"
    PREGNANCY_STATUS = "pregnancy_status"


class AudienceType(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    NURSE = "nurse"
    CAREGIVER = "caregiver"
    ADMINISTRATOR = "administrator"
    UNKNOWN = "unknown"


class LanguageInfo(BaseModel):
    language: str = "en"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    has_abbreviations: bool = False
    has_acronyms: bool = False
    has_informal_phrasing: bool = False
    has_typos: bool = False
    normalized_query: str = ""
    detected_abbreviations: list[str] = Field(default_factory=list)
    detected_acronyms: list[str] = Field(default_factory=list)


class MedicalEntity(BaseModel):
    entity_type: EntityType
    text: str
    normalized_text: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    start_pos: int = 0
    end_pos: int = 0
    attributes: dict[str, str] = Field(default_factory=dict)


class EntityResult(BaseModel):
    entities: list[MedicalEntity] = Field(default_factory=list)
    total: int = 0


class IntentCandidate(BaseModel):
    intent_type: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    sub_intent: str = ""
    matched_keywords: list[str] = Field(default_factory=list)


class IntentResult(BaseModel):
    primary_intent: IntentCandidate
    candidates: list[IntentCandidate] = Field(default_factory=list)
    total_candidates: int = 1


class SpecialtyCandidate(BaseModel):
    specialty: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    matched_terms: list[str] = Field(default_factory=list)


class SpecialtyResult(BaseModel):
    primary_specialty: SpecialtyCandidate
    candidates: list[SpecialtyCandidate] = Field(default_factory=list)
    total_candidates: int = 1


class UrgencyResult(BaseModel):
    level: str = "routine"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    indicators: list[str] = Field(default_factory=list)
    is_emergency: bool = False
    disclaimer: str = "This classification is advisory and must not replace clinical judgment."


class AudienceResult(BaseModel):
    audience: AudienceType
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    indicators: list[str] = Field(default_factory=list)


class RewriteResult(BaseModel):
    original_query: str
    rewritten_query: str
    expansions: list[str] = Field(default_factory=list)
    abbreviations_expanded: list[str] = Field(default_factory=list)
    normalized: bool = False
    context_injected: bool = False
    conversation_refs_resolved: bool = False


class ConversationContext(BaseModel):
    conversation_id: str | None = None
    previous_queries: list[str] = Field(default_factory=list)
    active_topics: list[str] = Field(default_factory=list)
    resolved_references: dict[str, str] = Field(default_factory=dict)
    message_count: int = 0
    has_context: bool = False


class QueryUnderstandingResult(BaseModel):
    original_query: str
    intent: IntentResult | None = None
    entities: EntityResult | None = None
    specialty: SpecialtyResult | None = None
    urgency: UrgencyResult | None = None
    audience: AudienceResult | None = None
    language: LanguageInfo | None = None
    rewrite: RewriteResult | None = None
    context: ConversationContext | None = None
    analysis_time_ms: float = 0.0
    analysis_scope: AnalysisScope = AnalysisScope.FULL


class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    conversation_id: str | None = None
    scope: AnalysisScope = AnalysisScope.FULL
    include_rewrite: bool = True
    include_entities: bool = True


class AnalyzeResponse(BaseModel):
    result: QueryUnderstandingResult
    query: str
    analysis_time_ms: float
