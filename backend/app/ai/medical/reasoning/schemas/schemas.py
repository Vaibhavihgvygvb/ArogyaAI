from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReasoningApproach(str, Enum):
    CLINICAL_REASONING = "clinical_reasoning"
    EVIDENCE_SYNTHESIS = "evidence_synthesis"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    DIFFERENTIAL_DIAGNOSIS = "differential_diagnosis"
    TREATMENT_PLANNING = "treatment_planning"
    RISK_ASSESSMENT = "risk_assessment"
    CONTEXTUAL_INFORMATION = "contextual_information"
    GENERAL_ANSWER = "general_answer"


class EvidencePriority(str, Enum):
    ESSENTIAL = "essential"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RetrievalStrategyType(str, Enum):
    SINGLE = "single"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    ITERATIVE = "iterative"
    FEDERATED = "federated"


class CompressionStrategy(str, Enum):
    NONE = "none"
    EXTRACTIVE = "extractive"
    ABSTRACTIVE = "abstractive"
    HYBRID = "hybrid"


class ReasoningStep(BaseModel):
    step_number: int
    description: str
    status: str = "pending"
    details: dict[str, Any] = Field(default_factory=dict)


class EvidenceRequirement(BaseModel):
    topic: str
    priority: EvidencePriority = EvidencePriority.MEDIUM
    query_variations: list[str] = Field(default_factory=list)
    min_results: int = 1
    required: bool = False


class ReasoningPlan(BaseModel):
    approach: ReasoningApproach = ReasoningApproach.EVIDENCE_SYNTHESIS
    reasoning_steps: list[ReasoningStep] = Field(default_factory=list)
    required_evidence_types: list[str] = Field(default_factory=list)
    output_structure: dict[str, Any] = Field(default_factory=dict)
    target_audience: str = "patient"
    complexity_level: str = "intermediate"
    disclaimer: str = "This reasoning plan is informational only and does not constitute medical advice."


class EvidencePlan(BaseModel):
    evidence_requirements: list[EvidenceRequirement] = Field(default_factory=list)
    retrieval_queries: list[str] = Field(default_factory=list)
    priority_filters: dict[str, Any] = Field(default_factory=dict)
    min_evidence_count: int = 3
    max_evidence_count: int = 20


class RetrievalPlan(BaseModel):
    strategy: RetrievalStrategyType = RetrievalStrategyType.SINGLE
    sub_queries: list[str] = Field(default_factory=list)
    weights: list[float] = Field(default_factory=list)
    top_k_per_query: int = 10
    merge_strategy: str = "score_weighted"
    filters: dict[str, Any] | None = None


class RankedContext(BaseModel):
    chunk_ids: list[str] = Field(default_factory=list)
    ranking_scores: list[float] = Field(default_factory=list)
    diversity_scores: list[float] = Field(default_factory=list)
    total_original: int = 0
    retained: int = 0


class CompressedContext(BaseModel):
    context: str = ""
    original_token_count: int = 0
    compressed_token_count: int = 0
    compression_ratio: float = 0.0
    removed_chunk_ids: list[str] = Field(default_factory=list)
    strategy: CompressionStrategy = CompressionStrategy.NONE


class AssembledPrompt(BaseModel):
    system_message: str = ""
    user_prompt: str = ""
    prompt_name: str = ""
    prompt_version: str = ""
    token_count: int = 0
    variables: dict[str, Any] = Field(default_factory=dict)


class CitationPlan(BaseModel):
    chunk_ids: list[str] = Field(default_factory=list)
    citation_map: dict[str, list[str]] = Field(default_factory=dict)
    coverage: float = 0.0
    priority_order: list[str] = Field(default_factory=list)


class ConfidencePlan(BaseModel):
    expected_retrieval_confidence: float = 0.0
    min_expected_confidence: float = 0.3
    confidence_factors: list[str] = Field(default_factory=list)
    confidence_thresholds: dict[str, float] = Field(default_factory=dict)


class SafetyPlan(BaseModel):
    constraints: list[str] = Field(default_factory=list)
    required_checks: list[str] = Field(default_factory=list)
    disclaimers: list[str] = Field(default_factory=list)
    prohibited_content_patterns: list[str] = Field(default_factory=list)


class ReasoningRequest(BaseModel):
    original_query: str = Field(..., min_length=1, max_length=10000)
    conversation_id: str | None = None
    approach_hint: ReasoningApproach | None = None
    top_k: int = Field(15, ge=1, le=100)
    filters: dict[str, Any] | None = None
    min_score: float | None = Field(None, ge=0.0, le=1.0)
    include_reasoning_plan: bool = True
    include_evidence_plan: bool = True
    include_retrieval_plan: bool = True
    include_context_ranking: bool = True
    include_context_compression: bool = True
    include_prompt_assembly: bool = True
    include_citation_plan: bool = True
    include_confidence_plan: bool = True
    include_safety_plan: bool = True
    max_context_tokens: int = Field(4096, ge=128, le=16384)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=16384)


class ReasoningResponse(BaseModel):
    request: ReasoningRequest
    analysis: dict[str, Any] | None = None
    reasoning_plan: ReasoningPlan | None = None
    evidence_plan: EvidencePlan | None = None
    retrieval_plan: RetrievalPlan | None = None
    ranked_context: RankedContext | None = None
    compressed_context: CompressedContext | None = None
    assembled_prompt: AssembledPrompt | None = None
    citation_plan: CitationPlan | None = None
    confidence_plan: ConfidencePlan | None = None
    safety_plan: SafetyPlan | None = None
    full_response: dict[str, Any] | None = None
    processing_time_ms: float = 0.0
    stages: dict[str, float] = Field(default_factory=dict)
