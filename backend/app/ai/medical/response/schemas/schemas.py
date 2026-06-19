from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ClinicalSectionType(str, Enum):
    SUMMARY = "summary"
    SYMPTOM_ANALYSIS = "symptom_analysis"
    DIFFERENTIAL_DIAGNOSIS = "differential_diagnosis"
    DIAGNOSTIC_APPROACH = "diagnostic_approach"
    TREATMENT_OPTIONS = "treatment_options"
    MEDICATION_INFO = "medication_info"
    RISK_FACTORS = "risk_factors"
    PREVENTION = "prevention"
    PROGNOSIS = "prognosis"
    FOLLOW_UP = "follow_up"
    LIFESTYLE = "lifestyle"
    MONITORING = "monitoring"
    COMPLICATIONS = "complications"
    REFERRAL = "referral"
    PATIENT_EDUCATION = "patient_education"
    EMERGENCY_GUIDANCE = "emergency_guidance"
    GENERAL_INFO = "general_info"


class ClinicalSection(BaseModel):
    section_type: ClinicalSectionType
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    priority: int = 0
    disclaimer: str | None = None


class StructuredAnswer(BaseModel):
    summary: str = ""
    sections: list[ClinicalSection] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    disclaimer: str | None = None
    formatted_text: str = ""


class Citation(BaseModel):
    source: str
    relevance_score: float = 0.0
    evidence_text: str | None = None
    reference_number: int = 0
    chunk_id: str = ""


class ResponseMetadata(BaseModel):
    model: str = ""
    provider: str = ""
    usage: dict[str, Any] | None = None
    processing_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    pipeline_stages: dict[str, float] = Field(default_factory=dict)
    finish_reason: str | None = None
    streaming: bool = False
    cached: bool = False


class GenerateRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000, description="Medical query")
    conversation_id: str | None = None
    reasoning_plan: dict[str, Any] | None = None
    assembled_prompt: dict[str, Any] | None = None
    approach_hint: str | None = None
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=16384)
    stream: bool = False
    top_k: int = Field(15, ge=1, le=100)
    filters: dict[str, Any] | None = None
    min_score: float | None = Field(None, ge=0.0, le=1.0)
    max_context_tokens: int = Field(4096, ge=128, le=16384)


class GenerateResponse(BaseModel):
    query: str
    answer: str
    structured_answer: StructuredAnswer | None = None
    sections: list[ClinicalSection] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    disclaimer: str | None = None
    conversation_id: str | None = None
    metadata: ResponseMetadata | None = None
    plan: dict[str, Any] | None = None
    processing_time_ms: float = 0.0


class StreamChunk(BaseModel):
    content: str
    done: bool = False
    chunk_index: int = 0
    finish_reason: str | None = None


class GenerateRequestSimple(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    conversation_id: str | None = None
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=16384)
    stream: bool = False
    top_k: int = Field(10, ge=1, le=100)
