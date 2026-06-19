from app.ai.evaluation.schemas import MetricCategory, MetricDefinition


RETRIEVAL_PRECISION = MetricDefinition(
    name="retrieval_precision",
    category=MetricCategory.RETRIEVAL,
    description="Precision of retrieved results",
)

RETRIEVAL_RECALL = MetricDefinition(
    name="retrieval_recall",
    category=MetricCategory.RETRIEVAL,
    description="Recall of retrieved results",
)

EVIDENCE_COVERAGE = MetricDefinition(
    name="evidence_coverage",
    category=MetricCategory.EVIDENCE,
    description="Coverage score of evidence validation",
)

EVIDENCE_CONFIDENCE = MetricDefinition(
    name="evidence_confidence",
    category=MetricCategory.EVIDENCE,
    description="Average confidence of verified evidence",
)

CITATION_COMPLETENESS = MetricDefinition(
    name="citation_completeness",
    category=MetricCategory.CITATION,
    description="Ratio of claims with citations",
)

SAFETY_APPROVAL_RATE = MetricDefinition(
    name="safety_approval_rate",
    category=MetricCategory.SAFETY,
    description="Rate of responses approved by safety",
)

HALLUCINATION_DETECTION_RATE = MetricDefinition(
    name="hallucination_detection_rate",
    category=MetricCategory.HALLUCINATION,
    description="Rate of hallucinations correctly detected",
)

UNSUPPORTED_CLAIM_RATE = MetricDefinition(
    name="unsupported_claim_rate",
    category=MetricCategory.UNSUPPORTED,
    description="Rate of unsupported claims detected",
)

EMERGENCY_DETECTION_ACCURACY = MetricDefinition(
    name="emergency_detection_accuracy",
    category=MetricCategory.EMERGENCY,
    description="Accuracy of emergency detection",
)

CONFIDENCE_CALIBRATION = MetricDefinition(
    name="confidence_calibration",
    category=MetricCategory.CONFIDENCE,
    description="Calibration of confidence scores",
)

RESPONSE_COMPLETENESS = MetricDefinition(
    name="response_completeness",
    category=MetricCategory.RESPONSE,
    description="Completeness of response",
)

PIPELINE_LATENCY = MetricDefinition(
    name="pipeline_latency_ms",
    category=MetricCategory.LATENCY,
    description="Total pipeline latency in milliseconds",
    min_value=0,
    max_value=10000,
    higher_is_better=False,
)

STANDARD_METRICS: dict[str, MetricDefinition] = {
    "retrieval_precision": RETRIEVAL_PRECISION,
    "retrieval_recall": RETRIEVAL_RECALL,
    "evidence_coverage": EVIDENCE_COVERAGE,
    "evidence_confidence": EVIDENCE_CONFIDENCE,
    "citation_completeness": CITATION_COMPLETENESS,
    "safety_approval_rate": SAFETY_APPROVAL_RATE,
    "hallucination_detection_rate": HALLUCINATION_DETECTION_RATE,
    "unsupported_claim_rate": UNSUPPORTED_CLAIM_RATE,
    "emergency_detection_accuracy": EMERGENCY_DETECTION_ACCURACY,
    "confidence_calibration": CONFIDENCE_CALIBRATION,
    "response_completeness": RESPONSE_COMPLETENESS,
    "pipeline_latency_ms": PIPELINE_LATENCY,
}
