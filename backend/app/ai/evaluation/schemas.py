from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class MetricCategory(str, Enum):
    RETRIEVAL = "retrieval"
    EVIDENCE = "evidence"
    CITATION = "citation"
    SAFETY = "safety"
    HALLUCINATION = "hallucination"
    UNSUPPORTED = "unsupported"
    EMERGENCY = "emergency"
    CONFIDENCE = "confidence"
    RESPONSE = "response"
    LATENCY = "latency"


class EvaluationMetric(BaseModel):
    name: str
    category: MetricCategory
    value: float
    weight: float = 1.0
    threshold: float | None = None
    passed: bool | None = None
    details: str | None = None


class EvaluationRun(BaseModel):
    id: str
    timestamp: datetime
    pipeline_name: str
    metrics: list[EvaluationMetric]
    summary_score: float = 0.0
    passed: bool = True
    metadata: dict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class EvaluationSuite(BaseModel):
    name: str
    description: str | None = None
    runs: list[EvaluationRun] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class MetricDefinition(BaseModel):
    name: str
    category: MetricCategory
    description: str
    min_value: float = 0.0
    max_value: float = 1.0
    higher_is_better: bool = True
    default_threshold: float | None = None
