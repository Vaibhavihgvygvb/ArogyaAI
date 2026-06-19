from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class HallucinationType(str, Enum):
    FABRICATED_MEDICATION = "fabricated_medication"
    FABRICATED_DISEASE = "fabricated_disease"
    FABRICATED_CITATION = "fabricated_citation"
    FABRICATED_GUIDELINE = "fabricated_guideline"
    FABRICATED_STATISTIC = "fabricated_statistic"
    FABRICATED_RECOMMENDATION = "fabricated_recommendation"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    CONTRADICTED_CLAIM = "contradicted_claim"
    UNKNOWN = "unknown"


class SupportLevel(str, Enum):
    FULLY_SUPPORTED = "fully_supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTORY = "contradictory"


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class EmergencyType(str, Enum):
    CHEST_PAIN = "chest_pain"
    STROKE_SYMPTOMS = "stroke_symptoms"
    SEVERE_BLEEDING = "severe_bleeding"
    SUICIDAL_IDEATION = "suicidal_ideation"
    ANAPHYLAXIS = "anaphylaxis"
    RESPIRATORY_DISTRESS = "respiratory_distress"
    LOSS_OF_CONSCIOUSNESS = "loss_of_consciousness"
    SEVERE_ALLERGIC_REACTION = "severe_allergic_reaction"
    OVERDOSE = "overdose"
    UNKNOWN = "unknown"


class PHIType(str, Enum):
    SSN = "ssn"
    EMAIL = "email"
    PHONE = "phone"
    AADHAAR = "aadhaar"
    PASSPORT = "passport"
    CREDIT_CARD = "credit_card"
    MEDICAL_RECORD_NUMBER = "medical_record_number"
    PATIENT_NAME = "patient_name"
    ADDRESS = "address"
    INSURANCE_ID = "insurance_id"
    DOB = "dob"
    UNKNOWN = "unknown"


class DisclaimerType(str, Enum):
    GENERAL_MEDICAL = "general_medical"
    EMERGENCY = "emergency"
    MEDICATION = "medication"
    MENTAL_HEALTH = "mental_health"
    PREGNANCY = "pregnancy"
    PEDIATRIC = "pediatric"
    CLINICAL_UNCERTAINTY = "clinical_uncertainty"


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    APPROVED_WITH_WARNINGS = "approved_with_warnings"
    ESCALATE = "escalate"
    REJECT = "reject"


class HallucinationResult(BaseModel):
    claim: str
    hallucination_type: HallucinationType
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_snippet: str | None = None
    details: str | None = None
    span_start: int = 0
    span_end: int = 0

    model_config = ConfigDict(from_attributes=True)


class HallucinationReport(BaseModel):
    results: list[HallucinationResult] = []
    total_claims: int = 0
    hallucinated_count: int = 0
    hallucination_rate: float = 0.0
    passed: bool = True
    summary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UnsupportedClaim(BaseModel):
    claim: str
    support_level: SupportLevel
    confidence: float = Field(..., ge=0.0, le=1.0)
    matched_evidence: list[str] = []
    missing_evidence: list[str] = []
    details: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UnsupportedClaimReport(BaseModel):
    claims: list[UnsupportedClaim] = []
    total_claims: int = 0
    supported_count: int = 0
    unsupported_count: int = 0
    contradictory_count: int = 0
    coverage_score: float = 0.0
    passed: bool = True
    summary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ClinicalRiskResult(BaseModel):
    risk_level: RiskLevel
    score: float = Field(..., ge=0.0, le=1.0)
    factors: list[str] = []
    confidence_impact: float = 0.0
    unsupported_impact: float = 0.0
    topic_sensitivity: float = 0.0
    emergency_indicators: list[str] = []
    details: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ClinicalRiskReport(BaseModel):
    results: list[ClinicalRiskResult] = []
    overall_risk: RiskLevel = RiskLevel.LOW
    max_risk_score: float = 0.0
    passed: bool = True
    summary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EmergencyResult(BaseModel):
    is_emergency: bool
    emergency_type: EmergencyType | None = None
    confidence: float = 0.0
    indicators: list[str] = []
    severity: str = "medium"
    recommended_action: str | None = None
    disclaimer_required: bool = True
    details: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EmergencyReport(BaseModel):
    results: list[EmergencyResult] = []
    has_emergency: bool = False
    max_severity: str = "none"
    requires_override: bool = False
    summary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PHIFinding(BaseModel):
    phi_type: PHIType
    value_preview: str
    location: str | None = None
    confidence: float = 0.0
    risk: str = "medium"

    model_config = ConfigDict(from_attributes=True)


class PHIValidationReport(BaseModel):
    findings: list[PHIFinding] = []
    total_findings: int = 0
    has_phi: bool = False
    passed: bool = True
    summary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DisclaimerConfig(BaseModel):
    disclaimer_type: DisclaimerType
    text: str
    severity: str = "informational"
    required: bool = True
    use_emergency_override: bool = False

    model_config = ConfigDict(from_attributes=True)


class DisclaimerResult(BaseModel):
    selected_disclaimers: list[DisclaimerConfig] = []
    has_emergency_disclaimer: bool = False
    has_medication_disclaimer: bool = False
    has_mental_health_disclaimer: bool = False
    summary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ComplianceCheck(BaseModel):
    check_name: str
    passed: bool
    severity: str = "medium"
    details: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ComplianceReport(BaseModel):
    checks: list[ComplianceCheck] = []
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    passed: bool = True
    summary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalResult(BaseModel):
    decision: ApprovalDecision
    reasons: list[str] = []
    warnings: list[str] = []
    requires_escalation: bool = False
    requires_override: bool = False
    summary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SafetyState(BaseModel):
    response_text: str = ""
    claims: list[str] = []
    evidence_report: dict | None = None
    hallucination_report: HallucinationReport | None = None
    unsupported_report: UnsupportedClaimReport | None = None
    risk_report: ClinicalRiskReport | None = None
    emergency_report: EmergencyReport | None = None
    phi_report: PHIValidationReport | None = None
    disclaimer_result: DisclaimerResult | None = None
    compliance_report: ComplianceReport | None = None
    approval_result: ApprovalResult | None = None
    config: dict = {}

    model_config = ConfigDict(from_attributes=True)


class PipelineResult(BaseModel):
    state: SafetyState
    pipeline_name: str = "clinical_safety"
    total_processing_time_ms: float = 0.0
    steps_completed: list[str] = []
    steps_skipped: list[str] = []
    errors: list[str] = []
    success: bool = True

    model_config = ConfigDict(from_attributes=True)


class SafetyServiceResult(BaseModel):
    passed: bool = False
    pipeline_result: PipelineResult | None = None
    approval: ApprovalResult | None = None
    summary: str | None = None
    warnings: list[str] = []
    errors: list[str] = []
    processing_time_ms: float = 0.0

    model_config = ConfigDict(from_attributes=True)
