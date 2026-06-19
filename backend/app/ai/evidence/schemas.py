from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"


class EvidenceType(str, Enum):
    DIRECT = "direct"
    STATISTICAL = "statistical"
    MECHANISTIC = "mechanistic"
    EXPERT_OPINION = "expert_opinion"
    GUIDELINE = "guideline"
    META_ANALYSIS = "meta_analysis"
    SYSTEMATIC_REVIEW = "systematic_review"
    CASE_STUDY = "case_study"
    UNKNOWN = "unknown"


class CitationStyle(str, Enum):
    AMA = "ama"
    APA = "apa"
    VANCOUVER = "vancouver"
    IEEE = "ieee"
    MLA = "mla"
    CHICAGO = "chicago"


class ConflictType(str, Enum):
    DIRECT = "direct"
    CONTRADICTORY = "contradictory"
    DIRECTIONAL = "directional"
    DOSAGE = "dosage"
    TIMING = "timing"
    CONTRAINDICATION = "contraindication"


class EvidenceSpan(BaseModel):
    text: str
    claim: str
    span_start: int = 0
    span_end: int = 0
    context: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerifiedSource(BaseModel):
    source_id: str
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    publication_date: str | None = None
    journal: str | None = None
    url: str | None = None
    doi: str | None = None
    evidence_type: EvidenceType = EvidenceType.UNKNOWN
    authority_score: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    recency_score: float = Field(default=0.0, ge=0.0, le=1.0)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    support_direction: str | None = None
    excerpt: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    span: EvidenceSpan
    verified: bool
    status: VerificationStatus
    supporting_sources: list[VerifiedSource] = Field(default_factory=list)
    contradicting_sources: list[VerifiedSource] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_summary: str | None = None
    verification_details: str | None = None
    processing_time_ms: float = 0.0


class Citation(BaseModel):
    citation_id: str
    span_index: int = 0
    evidence_text: str
    source: VerifiedSource
    citation_number: int = 0
    inline_ref: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CitationGroup(BaseModel):
    claim: str
    citations: list[Citation] = Field(default_factory=list)
    total_citations: int = 0


class FormattedCitation(BaseModel):
    style: CitationStyle
    text: str
    markdown: str
    bibtex: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    reference_list: list[str] = Field(default_factory=list)


class CoverageGap(BaseModel):
    claim: str
    gap_type: str
    severity: str = "medium"
    description: str | None = None
    suggested_sources: list[str] = Field(default_factory=list)


class CoverageResult(BaseModel):
    total_spans: int = 0
    verified_spans: int = 0
    unverified_spans: int = 0
    partially_verified_spans: int = 0
    coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_density: float = 0.0
    gaps: list[CoverageGap] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ConflictResult(BaseModel):
    span_index: int = 0
    claim: str
    conflict_type: ConflictType
    sources: list[VerifiedSource] = Field(default_factory=list)
    severity: str = "medium"
    description: str | None = None
    resolution: str | None = None


class ConfidenceBreakdown(BaseModel):
    category: str
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    weight: float = 0.0
    details: str | None = None


class ConfidenceResult(BaseModel):
    overall: float = Field(default=0.0, ge=0.0, le=1.0)
    verification_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    citation_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    coverage_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_quality_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    suitable_for_ai: bool = False
    breakdown: list[ConfidenceBreakdown] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProvenanceAction(str, Enum):
    VERIFICATION = "verification"
    CITATION = "citation"
    COVERAGE = "coverage"
    CONFLICT = "conflict"
    CONFIDENCE = "confidence"
    RANKING = "ranking"
    PIPELINE = "pipeline"
    EXPLANATION = "explanation"


class ProvenanceEntry(BaseModel):
    action: ProvenanceAction
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    engine_name: str
    input_summary: str | None = None
    output_summary: str | None = None
    processing_time_ms: float = 0.0
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProvenanceGraph(BaseModel):
    entries: list[ProvenanceEntry] = Field(default_factory=list)
    total_time_ms: float = 0.0
    engine_count: int = 0


class ExplanationComponent(BaseModel):
    component: str
    detail: str
    score: float = 0.0


class ExplanationResult(BaseModel):
    summary: str | None = None
    components: list[ExplanationComponent] = Field(default_factory=list)
    narrative: str | None = None
    verification_summary: str | None = None
    citation_summary: str | None = None
    coverage_summary: str | None = None
    conflict_summary: str | None = None
    confidence_summary: str | None = None
    recommendations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceState(BaseModel):
    spans: list[EvidenceSpan] = Field(default_factory=list)
    verification_results: list[VerificationResult] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    citation_groups: list[CitationGroup] = Field(default_factory=list)
    formatted_citation: FormattedCitation | None = None
    coverage: CoverageResult | None = None
    ranked_sources: list[VerifiedSource] = Field(default_factory=list)
    conflicts: list[ConflictResult] = Field(default_factory=list)
    confidence: ConfidenceResult | None = None
    provenance: list[ProvenanceEntry] = Field(default_factory=list)
    explanation: ExplanationResult | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineResult(BaseModel):
    state: EvidenceState
    pipeline_name: str = "default"
    total_processing_time_ms: float = 0.0
    steps_completed: list[str] = Field(default_factory=list)
    steps_skipped: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    success: bool = True


class ServiceResult(BaseModel):
    passed: bool = False
    pipeline_result: PipelineResult | None = None
    summary: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0
