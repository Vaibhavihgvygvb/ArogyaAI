from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Specialty(str, Enum):
    CARDIOLOGY = "cardiology"
    NEUROLOGY = "neurology"
    ONCOLOGY = "oncology"
    PEDIATRICS = "pediatrics"
    ORTHOPEDICS = "orthopedics"
    DERMATOLOGY = "dermatology"
    GASTROENTEROLOGY = "gastroenterology"
    PULMONOLOGY = "pulmonology"
    ENDOCRINOLOGY = "endocrinology"
    PSYCHIATRY = "psychiatry"
    OPHTHALMOLOGY = "ophthalmology"
    UROLOGY = "urology"
    NEPHROLOGY = "nephrology"
    RHEUMATOLOGY = "rheumatology"
    INFECTIOUS_DISEASE = "infectious_disease"
    GENERAL_MEDICINE = "general_medicine"
    EMERGENCY_MEDICINE = "emergency_medicine"
    ANESTHESIOLOGY = "anesthesiology"
    PATHOLOGY = "pathology"
    RADIOLOGY = "radiology"


class IntentType(str, Enum):
    DIAGNOSIS = "diagnosis"
    TREATMENT = "treatment"
    MEDICATION = "medication"
    SYMPTOM_ASSESSMENT = "symptom_assessment"
    PROCEDURE = "procedure"
    PREVENTION = "prevention"
    PROGNOSIS = "prognosis"
    ETIOLOGY = "etiology"
    EPIDEMIOLOGY = "epidemiology"
    GENERAL_INQUIRY = "general_inquiry"


class UrgencyLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ROUTINE = "routine"


class MedicalIntent(BaseModel):
    intent_type: IntentType
    specialty: Specialty
    urgency: UrgencyLevel = UrgencyLevel.ROUTINE
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    keywords: list[str] = Field(default_factory=list)
    sub_specialty: str | None = None


class QueryRewrite(BaseModel):
    original_query: str
    rewritten_query: str
    expansions: list[str] = Field(default_factory=list)
    abbreviations_expanded: list[str] = Field(default_factory=list)
    context_injected: bool = False
    rewrite_reason: str | None = None


class MedicalContext(BaseModel):
    context: str
    token_count: int = 0
    chunk_count: int = 0
    specialties: list[Specialty] = Field(default_factory=list)
    truncated: bool = False
    retrieval_time_ms: float = 0.0


class ConfidenceScore(BaseModel):
    overall: float = Field(default=0.0, ge=0.0, le=1.0)
    retrieval_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    generation_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    citation_coverage: float = Field(default=0.0, ge=0.0, le=1.0)


class SafetyCheckResult(BaseModel):
    passed: bool = True
    hallucination_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    unsafe_advice_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    contradiction_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    reason: str | None = None


class CitationEntry(BaseModel):
    chunk_id: str
    knowledge_id: str
    document_id: str | None = None
    source: str | None = None
    relevance_score: float = 0.0
    evidence_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class MedicalReasoning(BaseModel):
    chain_of_thought: str | None = None
    clinical_rationale: str | None = None
    differential_considerations: list[str] = Field(default_factory=list)
    evidence_summary: str | None = None
    limitations: list[str] = Field(default_factory=list)


class MedicalMetadata(BaseModel):
    processing_time_ms: float = 0.0
    pipeline_stages: dict[str, float] = Field(default_factory=dict)
    model: str = ""
    provider: str = ""
    usage: dict[str, Any] | None = None


class MedicalQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000, description="Medical query")
    conversation_id: str | None = Field(None, description="Conversation ID for context")
    specialty: Specialty | None = Field(None, description="Hint for medical specialty")
    top_k: int = Field(10, ge=1, le=100, description="Max chunks to retrieve")
    filters: dict[str, Any] | None = Field(None, description="Metadata filters")
    min_score: float | None = Field(None, ge=0.0, le=1.0, description="Min similarity score")
    include_reasoning: bool = True
    include_citations: bool = True
    max_context_tokens: int = Field(2048, ge=128, le=16384, description="Max context tokens")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="Generation temperature")
    max_tokens: int | None = Field(None, ge=1, le=16384, description="Max generation tokens")


class MedicalResponse(BaseModel):
    answer: str
    intent: MedicalIntent | None = None
    rewrite: QueryRewrite | None = None
    reasoning: MedicalReasoning | None = None
    citations: list[CitationEntry] = Field(default_factory=list)
    confidence: ConfidenceScore | None = None
    safety: SafetyCheckResult | None = None
    metadata: MedicalMetadata | None = None
    conversation_id: str | None = None


class MedicalSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000, description="Medical query")
    specialty: Specialty | None = None
    top_k: int = Field(10, ge=1, le=100)
    filters: dict[str, Any] | None = None
    min_score: float | None = Field(None, ge=0.0, le=1.0)
    include_chunks: bool = True
    rerank: bool = True


class MedicalSearchResponse(BaseModel):
    results: list[CitationEntry]
    total: int
    query: str
    intent: MedicalIntent | None = None
    query_time_ms: float = 0.0
