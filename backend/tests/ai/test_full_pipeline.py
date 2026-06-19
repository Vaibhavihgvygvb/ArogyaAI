"""End-to-end AI pipeline integration tests using only mocks (no real LLMs).

Validates every stage: authentication -> request validation -> medical query
understanding -> evidence -> clinical safety -> mock provider consistency.
"""

import hashlib

import pytest
from fastapi.testclient import TestClient

from app.ai.clinical_safety.pipelines.pipeline import ClinicalSafetyPipeline
from app.ai.clinical_safety.schemas import (
    ApprovalDecision,
    ApprovalResult,
    ClinicalRiskReport,
    ClinicalRiskResult,
    ComplianceCheck,
    ComplianceReport,
    DisclaimerConfig,
    DisclaimerResult,
    DisclaimerType,
    EmergencyReport,
    EmergencyResult,
    EmergencyType,
    HallucinationReport,
    HallucinationResult,
    HallucinationType,
    PHIFinding,
    PHIValidationReport,
    PHIType,
    PipelineResult as SafetyPipelineResult,
    RiskLevel,
    SafetyServiceResult,
    SafetyState,
    SupportLevel,
    UnsupportedClaim,
    UnsupportedClaimReport,
)
from app.ai.clinical_safety.services._service import ClinicalSafetyService
from app.ai.embeddings.providers.mock import MockEmbeddingProvider
from app.ai.evidence.config import EvidenceConfig
from app.ai.evidence.pipeline import EvidencePipeline
from app.ai.evidence.schemas import (
    Citation,
    CitationStyle,
    ConfidenceBreakdown,
    ConfidenceResult,
    CoverageResult,
    EvidenceSpan,
    EvidenceState,
    ExplanationResult,
    FormattedCitation,
    PipelineResult as EvidencePipelineResult,
    ServiceResult,
    VerificationResult,
    VerificationStatus,
    VerifiedSource,
)
from app.ai.evidence.service import EvidenceService
from app.ai.providers.base import CompletionResponse
from app.ai.providers.mock import MockLLMProvider
from app.api.deps import get_current_user
from app.main import app
from app.models.enums import UserRole
from app.models.user import User


# ---------------------------------------------------------------------------
# Mock engines for the Evidence pipeline
# ---------------------------------------------------------------------------

class MockVerifier:
    async def verify(self, spans, state=None):
        return [
            VerificationResult(
                span=s,
                verified=True,
                status=VerificationStatus.VERIFIED,
                supporting_sources=[
                    VerifiedSource(
                        source_id="s1",
                        support_direction="supporting",
                        authority_score=0.8,
                        relevance_score=0.9,
                        recency_score=0.7,
                        quality_score=0.85,
                    )
                ],
                contradicting_sources=[],
                confidence=0.9,
                evidence_summary=f"Verified: {s.claim}",
                verification_details="Mock verification",
            )
            for s in spans
        ]


class MockCitationGenerator:
    async def generate(self, verification_results, state=None):
        citations = []
        for i, vr in enumerate(verification_results):
            for j, src in enumerate(vr.supporting_sources):
                citations.append(
                    Citation(
                        citation_id=f"cit_{i}_{j}",
                        span_index=i,
                        evidence_text=vr.span.claim,
                        source=src,
                        confidence=vr.confidence,
                    )
                )
        return citations

    async def group_by_claim(self, citations):
        return []


class MockCitationFormatter:
    async def format(self, citations, style=CitationStyle.AMA):
        return FormattedCitation(style=style, text="", markdown="")


class MockCoverageAnalyzer:
    def __init__(self, coverage_result=None):
        self._coverage_result = coverage_result

    async def analyze(self, verification_results, state=None):
        if self._coverage_result is not None:
            return self._coverage_result
        return CoverageResult(
            total_spans=len(verification_results),
            verified_spans=len(verification_results),
            coverage_score=1.0,
        )


class MockConflictDetector:
    def __init__(self, conflicts=None):
        self._conflicts = conflicts

    async def detect(self, verification_results, state=None):
        if self._conflicts is not None:
            return self._conflicts
        return []


class MockSourceRanker:
    async def rank(self, sources, state=None):
        return sources


class MockConfidenceCalculator:
    def __init__(self, confidence_result=None):
        self._confidence_result = confidence_result

    async def calculate(
        self, verification_results, coverage=None, conflicts=None, citations=None, state=None
    ):
        if self._confidence_result is not None:
            return self._confidence_result
        return ConfidenceResult(
            overall=0.85,
            verification_confidence=0.9,
            citation_confidence=0.8,
            coverage_confidence=1.0,
            source_quality_confidence=0.8,
            suitable_for_ai=True,
            breakdown=[ConfidenceBreakdown(category="Verification", score=0.9, weight=0.35)],
        )


class MockProvenanceTracker:
    async def track(self, entry, state=None):
        return [entry]

    async def get_graph(self, entries):
        return {"entries": [], "total_time_ms": 0.0, "engine_count": 0}


class MockExplainabilityProvider:
    async def explain(
        self, verification_results, coverage=None, conflicts=None, confidence=None,
        citations=None, state=None,
    ):
        return ExplanationResult(summary="Analysis complete.")


class MockBrokenEvidencePipeline:
    async def run(self, spans, citation_style=CitationStyle.AMA, config_override=None):
        raise RuntimeError("Evidence pipeline crashed")


# ---------------------------------------------------------------------------
# Mock engines for the Clinical Safety pipeline
# ---------------------------------------------------------------------------

class MockHallucinationDetector:
    def __init__(self, hallucination_rate=0.0):
        self._rate = hallucination_rate

    def _extract_claims(self, text: str) -> list[str]:
        return [s.strip() for s in text.split(".") if len(s.strip()) > 5][:100]

    async def detect(self, text, claims, evidence=None):
        has_hallu = self._rate > 0
        return HallucinationReport(
            results=[
                HallucinationResult(
                    claim=claims[0] if claims else "test",
                    hallucination_type=(
                        HallucinationType.FABRICATED_MEDICATION if has_hallu
                        else HallucinationType.UNKNOWN
                    ),
                    confidence=min(1.0, self._rate + 0.1) if has_hallu else 0.1,
                    details="Mock hallucination detection.",
                )
            ] if has_hallu else [],
            total_claims=len(claims) if claims else (1 if has_hallu else 0),
            hallucinated_count=1 if has_hallu else 0,
            hallucination_rate=self._rate,
            passed=self._rate < 0.5,
            summary=f"Mock: rate {self._rate:.0%}.",
        )


class MockUnsupportedDetector:
    def __init__(self, coverage_score=1.0):
        self._score = coverage_score

    async def detect(self, claims, evidence=None):
        unsupported_count = 0 if self._score >= 0.5 else len(claims)
        return UnsupportedClaimReport(
            claims=[
                UnsupportedClaim(
                    claim=c,
                    support_level=SupportLevel.FULLY_SUPPORTED if self._score >= 0.5
                    else SupportLevel.UNSUPPORTED,
                    confidence=0.9 if self._score >= 0.5 else 0.4,
                    matched_evidence=["ref"] if self._score >= 0.5 else [],
                    missing_evidence=[] if self._score >= 0.5 else ["ref"],
                )
                for c in claims
            ],
            total_claims=len(claims),
            supported_count=len(claims) if self._score >= 0.5 else 0,
            unsupported_count=unsupported_count,
            contradictory_count=0,
            coverage_score=self._score,
            passed=self._score >= 0.5,
            summary=f"Mock: coverage {self._score:.0%}.",
        )


class MockRiskEngine:
    def __init__(self, risk_level=RiskLevel.LOW):
        self._level = risk_level

    async def assess(self, hallucination_report, unsupported_report, emergency_report=None):
        scores = {RiskLevel.LOW: 0.1, RiskLevel.MODERATE: 0.3, RiskLevel.HIGH: 0.6, RiskLevel.CRITICAL: 0.8}
        return ClinicalRiskReport(
            results=[
                ClinicalRiskResult(
                    risk_level=self._level,
                    score=scores.get(self._level, 0.1),
                    factors=[f"Mock factor: {self._level.value}"],
                )
            ],
            overall_risk=self._level,
            max_risk_score=scores.get(self._level, 0.1),
            passed=self._level in (RiskLevel.LOW, RiskLevel.MODERATE),
            summary=f"Mock risk: {self._level.value}.",
        )


class MockEmergencyDetector:
    def __init__(self, has_emergency=False, severity="none"):
        self._has_emergency = has_emergency
        self._severity = severity

    async def detect(self, text, claims):
        return EmergencyReport(
            results=[
                EmergencyResult(
                    is_emergency=True,
                    emergency_type=EmergencyType.CHEST_PAIN,
                    confidence=0.95,
                    indicators=["chest pain"],
                    severity=self._severity,
                    recommended_action="Seek immediate attention.",
                    disclaimer_required=True,
                )
            ] if self._has_emergency else [],
            has_emergency=self._has_emergency,
            max_severity=self._severity,
            requires_override=self._severity in ("high", "critical"),
            summary="Mock emergency." if self._has_emergency else "No emergency.",
        )


class MockPHIValidator:
    def __init__(self, has_phi=False):
        self._has_phi = has_phi

    async def validate(self, text):
        return PHIValidationReport(
            findings=[
                PHIFinding(
                    phi_type=PHIType.SSN,
                    value_preview="***",
                    location="pos 0-11",
                    confidence=0.9,
                    risk="high",
                )
            ] if self._has_phi else [],
            total_findings=1 if self._has_phi else 0,
            has_phi=self._has_phi,
            passed=True,
            summary=f"{'Found PHI' if self._has_phi else 'No PHI'}.",
        )


class MockDisclaimerEngine:
    async def select(self, risk_report, emergency_report, phi_report=None):
        return DisclaimerResult(
            selected_disclaimers=[
                DisclaimerConfig(
                    disclaimer_type=DisclaimerType.GENERAL_MEDICAL,
                    text="For educational purposes only.",
                    severity="informational",
                    required=True,
                    use_emergency_override=False,
                )
            ],
            summary="Selected 1 disclaimer(s).",
        )

    async def get_disclaimers(self):
        return []


class MockComplianceValidator:
    def __init__(self, passed=True):
        self._passed = passed

    async def validate(self, hallucination_report, unsupported_report, disclaimer_result,
                       risk_report=None):
        return ComplianceReport(
            checks=[
                ComplianceCheck(check_name="Hallucination Check", passed=self._passed,
                                severity="high"),
            ],
            total_checks=1,
            passed_checks=1 if self._passed else 0,
            failed_checks=0 if self._passed else 1,
            passed=self._passed,
            summary="1/1 passed." if self._passed else "0/1 passed.",
        )


class MockApprovalEngine:
    def __init__(self, decision=ApprovalDecision.APPROVED):
        self._decision = decision

    async def approve(self, hallucination_report, unsupported_report, risk_report,
                      compliance_report, disclaimer_result, emergency_report=None):
        return ApprovalResult(
            decision=self._decision,
            reasons=["Mock approval."],
            warnings=[] if self._decision == ApprovalDecision.APPROVED else ["Warning: high risk"],
            requires_escalation=self._decision == ApprovalDecision.ESCALATE,
            requires_override=self._decision == ApprovalDecision.REJECT,
            summary=f"Mock: {self._decision.value}.",
        )


class MockBrokenSafetyPipeline:
    async def run(self, text, claims=None, evidence=None, config_override=None):
        raise RuntimeError("Safety pipeline crashed")


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_evidence_span(claim="Aspirin reduces heart attack risk"):
    return EvidenceSpan(text=claim, claim=claim, span_start=0, span_end=len(claim))


def make_evidence_pipeline(**engine_overrides):
    defaults = dict(
        verifier=MockVerifier(),
        citation_generator=MockCitationGenerator(),
        citation_formatter=MockCitationFormatter(),
        coverage_analyzer=MockCoverageAnalyzer(),
        source_ranker=MockSourceRanker(),
        conflict_detector=MockConflictDetector(),
        confidence_calculator=MockConfidenceCalculator(),
        provenance_tracker=MockProvenanceTracker(),
        explainability_provider=MockExplainabilityProvider(),
    )
    defaults.update(engine_overrides)
    return EvidencePipeline(**defaults)


def make_safety_pipeline(**engine_overrides):
    defaults = dict(
        hallucination_detector=MockHallucinationDetector(),
        unsupported_detector=MockUnsupportedDetector(),
        risk_engine=MockRiskEngine(),
        emergency_detector=MockEmergencyDetector(),
        phi_validator=MockPHIValidator(),
        disclaimer_engine=MockDisclaimerEngine(),
        compliance_validator=MockComplianceValidator(),
        approval_engine=MockApprovalEngine(),
    )
    defaults.update(engine_overrides)
    return ClinicalSafetyPipeline(**defaults)


def _override_get_current_user():
    return User(
        id=1,
        email="doctor@test.com",
        hashed_password="hashed_placeholder",
        role=UserRole.DOCTOR,
        is_active=True,
        is_verified=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEndToEndPipeline:
    """TestClient-based end-to-end tests through the FastAPI app."""

    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def _auth_headers(self):
        return {"Authorization": "Bearer mock-token"}

    # -- Empty request rejection -------------------------------------------

    def test_empty_request_rejected(self):
        """POST /ai/medical/analyze with empty body returns 422."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post("/ai/medical/analyze", json={})
        assert response.status_code == 422

    def test_empty_query_rejected(self):
        """POST /ai/medical/analyze with empty query string returns 422."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post("/ai/medical/analyze", json={"query": ""})
        assert response.status_code == 422

    # -- Unauthorized access -----------------------------------------------

    def test_unauthorized_access(self):
        """Missing auth token returns 401."""
        client = TestClient(app)
        response = client.post("/ai/medical/analyze", json={"query": "headache"})
        assert response.status_code == 401

    def test_unauthorized_access_evidence(self):
        """Evidence endpoint without auth returns 401."""
        client = TestClient(app)
        span = make_evidence_span()
        response = client.post(
            "/ai/evidence/validate",
            json={"spans": [span.model_dump()]},
        )
        assert response.status_code == 401

    def test_unauthorized_access_safety(self):
        """Safety endpoint without auth returns 401."""
        client = TestClient(app)
        response = client.post(
            "/ai/safety/validate",
            json={"response_text": "Take aspirin daily."},
        )
        assert response.status_code == 401

    # -- Health endpoints --------------------------------------------------

    def test_root_endpoint(self):
        """GET / returns welcome message."""
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "ArogyaAI" in data["message"]

    def test_health_endpoint(self):
        """GET /health returns health status."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "application" in data

    # -- Query understanding endpoint --------------------------------------

    def test_query_understanding_endpoint(self):
        """POST /ai/medical/analyze with valid query returns analysis."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/medical/analyze",
            json={"query": "What causes headache and fever?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "query" in data
        assert "analysis_time_ms" in data
        assert data["query"] == "What causes headache and fever?"
        result = data["result"]
        assert "original_query" in result
        assert "intent" in result
        assert "entities" in result

    # -- Intent detection --------------------------------------------------

    def test_intent_detection(self):
        """POST /ai/medical/intent returns IntentResult."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/medical/intent",
            json={"query": "What causes headache?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "primary_intent" in data
        assert "candidates" in data
        assert data["primary_intent"]["intent_type"] is not None
        assert "confidence" in data["primary_intent"]

    def test_intent_detection_empty_query(self):
        """POST /ai/medical/intent with empty query returns 422."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post("/ai/medical/intent", json={"query": ""})
        assert response.status_code == 422

    # -- Entity extraction -------------------------------------------------

    def test_entity_extraction(self):
        """POST /ai/medical/entities returns EntityResult."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/medical/entities",
            json={"query": "Patient has fever and cough since 3 days"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert "total" in data
        assert isinstance(data["entities"], list)

    # -- Query rewrite -----------------------------------------------------

    def test_query_rewrite(self):
        """POST /ai/medical/rewrite returns RewriteResult."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/medical/rewrite",
            json={"query": "What is HTN?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "original_query" in data
        assert "rewritten_query" in data

    # -- Evidence endpoint -------------------------------------------------

    def test_evidence_endpoint(self):
        """POST /ai/evidence/validate with spans returns ServiceResult."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        span = make_evidence_span()
        response = client.post(
            "/ai/evidence/validate",
            json={"spans": [span.model_dump()]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "passed" in data
        assert "summary" in data
        assert "processing_time_ms" in data

    def test_evidence_endpoint_empty_spans(self):
        """POST /ai/evidence/validate with empty spans returns 422."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/evidence/validate",
            json={"spans": []},
        )
        assert response.status_code == 422

    def test_evidence_verify_endpoint(self):
        """POST /ai/evidence/verify returns PipelineResult."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        span = make_evidence_span()
        response = client.post(
            "/ai/evidence/verify",
            json={"spans": [span.model_dump()]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "state" in data
        assert "success" in data

    def test_evidence_citations_endpoint(self):
        """POST /ai/evidence/citations returns PipelineResult."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        span = make_evidence_span()
        response = client.post(
            "/ai/evidence/citations",
            json={"spans": [span.model_dump()]},
        )
        assert response.status_code == 200

    def test_evidence_health_endpoint(self):
        """GET /ai/evidence/health returns healthy."""
        client = TestClient(app)
        response = client.get("/ai/evidence/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "evidence_intelligence"

    # -- Safety endpoint ---------------------------------------------------

    def test_safety_endpoint(self):
        """POST /ai/safety/validate with response text returns SafetyServiceResult."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/safety/validate",
            json={"response_text": "Take aspirin daily for heart health."},
        )
        assert response.status_code == 200
        data = response.json()
        assert "passed" in data
        assert "summary" in data
        assert "processing_time_ms" in data

    def test_safety_endpoint_empty_text(self):
        """POST /ai/safety/validate with empty text returns 422."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/safety/validate",
            json={"response_text": ""},
        )
        assert response.status_code == 422

    def test_safety_endpoint_with_claims(self):
        """POST /ai/safety/validate with claims and evidence."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/safety/validate",
            json={
                "response_text": "Aspirin reduces heart attack risk.",
                "claims": ["Aspirin reduces heart attack risk"],
                "evidence": {"Aspirin": "true"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "passed" in data
        assert "approval" in data

    def test_safety_hallucination_endpoint(self):
        """POST /ai/safety/hallucination returns HallucinationReport."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/safety/hallucination",
            json={
                "response_text": "A new drug Xylomab reduces heart attack risk by 100%.",
                "claims": ["Xylomab reduces risk"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "hallucination_rate" in data
        assert "passed" in data

    def test_safety_emergency_endpoint(self):
        """POST /ai/safety/emergency with emergency text returns EmergencyReport."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/safety/emergency",
            json={
                "response_text": "Patient is experiencing chest pain and shortness of breath.",
                "claims": ["chest pain", "shortness of breath"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "has_emergency" in data
        assert "results" in data
        assert "max_severity" in data

    def test_safety_phi_endpoint(self):
        """POST /ai/safety/phi with PHI text returns PHIValidationReport."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/safety/phi",
            json={"response_text": "Patient SSN is 123-45-6789 and email is test@test.com."},
        )
        assert response.status_code == 200
        data = response.json()
        assert "findings" in data
        assert "total_findings" in data
        assert "has_phi" in data
        assert "passed" in data

    def test_safety_risk_endpoint(self):
        """POST /ai/safety/risk returns ClinicalRiskReport."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/safety/risk",
            json={"response_text": "Aspirin reduces heart attack risk."},
        )
        assert response.status_code == 200
        data = response.json()
        assert "overall_risk" in data
        assert "results" in data

    def test_safety_unsupported_endpoint(self):
        """POST /ai/safety/unsupported returns UnsupportedClaimReport."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/safety/unsupported",
            json={
                "response_text": "Test claim.",
                "claims": ["Test claim"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "claims" in data
        assert "coverage_score" in data

    def test_safety_disclaimer_endpoint(self):
        """POST /ai/safety/disclaimer returns DisclaimerResult."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/safety/disclaimer",
            json={"response_text": "Take medication daily."},
        )
        assert response.status_code == 200
        data = response.json()
        assert "selected_disclaimers" in data
        assert "summary" in data

    def test_safety_compliance_endpoint(self):
        """POST /ai/safety/compliance returns ComplianceReport."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/safety/compliance",
            json={"response_text": "Aspirin reduces risk."},
        )
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "passed" in data

    def test_safety_approval_endpoint(self):
        """POST /ai/safety/approval returns ApprovalResult."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.post(
            "/ai/safety/approval",
            json={"response_text": "Aspirin reduces heart attack risk."},
        )
        assert response.status_code == 200
        data = response.json()
        assert "decision" in data
        assert "reasons" in data

    def test_safety_health_endpoint(self):
        """GET /ai/safety/health returns healthy."""
        client = TestClient(app)
        response = client.get("/ai/safety/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "clinical_safety"

    # -- Specialty listing endpoints ---------------------------------------

    def test_specialties_endpoint(self):
        """GET /ai/medical/specialties returns list of specialties."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.get("/ai/medical/specialties")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "name" in data[0]
        assert "value" in data[0]

    def test_intents_list_endpoint(self):
        """GET /ai/medical/intents returns list of intents."""
        app.dependency_overrides[get_current_user] = _override_get_current_user
        client = TestClient(app)
        response = client.get("/ai/medical/intents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "name" in data[0]
        assert "value" in data[0]


class TestCrossModuleIntegration:
    """Tests that evidence and safety services compose correctly."""

    @pytest.mark.asyncio
    async def test_evidence_service_result_shape(self):
        """ServiceResult has the expected fields for downstream consumption."""
        service = EvidenceService(pipeline=make_evidence_pipeline())
        result = await service.validate_evidence([make_evidence_span()])
        assert isinstance(result, ServiceResult)
        assert result.passed is True
        assert result.pipeline_result is not None
        assert result.pipeline_result.success is True
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_safety_service_result_shape(self):
        """SafetyServiceResult has the expected fields."""
        service = ClinicalSafetyService(pipeline=make_safety_pipeline())
        result = await service.validate(
            response_text="Aspirin reduces heart attack risk.",
        )
        assert isinstance(result, SafetyServiceResult)
        assert result.passed is True
        assert result.pipeline_result is not None
        assert result.approval is not None
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_evidence_result_consumed_by_safety(self):
        """Evidence ServiceResult.passed can be forwarded to safety as input."""
        evidence_service = EvidenceService(pipeline=make_evidence_pipeline())
        evidence_result = await evidence_service.validate_evidence(
            [make_evidence_span("Aspirin reduces risk")],
        )

        assert evidence_result.passed is True
        assert evidence_result.summary is not None

        safety_service = ClinicalSafetyService(pipeline=make_safety_pipeline())
        safety_result = await safety_service.validate(
            response_text="Aspirin reduces heart attack risk.",
            claims=["Aspirin reduces heart attack risk"],
            evidence={"evidence_passed": evidence_result.passed},
        )
        assert isinstance(safety_result, SafetyServiceResult)

    @pytest.mark.asyncio
    async def test_evidence_result_with_citation_style(self):
        """EvidenceService respects citation_style parameter."""
        service = EvidenceService(pipeline=make_evidence_pipeline())
        for style in (CitationStyle.AMA, CitationStyle.APA, CitationStyle.IEEE):
            result = await service.validate_evidence(
                [make_evidence_span()],
                citation_style=style,
            )
            assert isinstance(result, ServiceResult)
            assert result.passed is True

    @pytest.mark.asyncio
    async def test_safety_validates_hallucinated_evidence(self):
        """Safety validation detects hallucinated content properly."""
        pipeline = make_safety_pipeline(
            hallucination_detector=MockHallucinationDetector(hallucination_rate=0.8),
            approval_engine=MockApprovalEngine(decision=ApprovalDecision.REJECT),
        )
        service = ClinicalSafetyService(pipeline=pipeline)
        result = await service.validate(
            response_text="FabricatedDrugXYZ cures all diseases instantly.",
            claims=["FabricatedDrugXYZ cures all diseases"],
            evidence={"FabricatedDrugXYZ": "false"},
        )
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_safety_phi_detection(self):
        """Safety PHI validation detects sensitive data."""
        pipeline = make_safety_pipeline(
            phi_validator=MockPHIValidator(has_phi=True),
        )
        service = ClinicalSafetyService(pipeline=pipeline)
        result = await service.validate_phi(text="Patient SSN is 123-45-6789.")
        assert result.has_phi is True
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_safety_emergency_detection(self):
        """Safety emergency detection flags urgent content."""
        pipeline = make_safety_pipeline(
            emergency_detector=MockEmergencyDetector(has_emergency=True, severity="critical"),
            approval_engine=MockApprovalEngine(decision=ApprovalDecision.ESCALATE),
        )
        service = ClinicalSafetyService(pipeline=pipeline)
        result = await service.validate(
            response_text="Patient is having chest pain and difficulty breathing.",
        )
        assert any("Emergency detected" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_evidence_empty_spans(self):
        """Empty evidence spans return passed with no-op summary."""
        service = EvidenceService(pipeline=make_evidence_pipeline())
        result = await service.validate_evidence([])
        assert result.passed is True
        assert result.summary == "No evidence spans to validate."
        assert result.processing_time_ms == 0.0

    @pytest.mark.asyncio
    async def test_safety_empty_text(self):
        """Empty safety response text returns failed."""
        service = ClinicalSafetyService(pipeline=make_safety_pipeline())
        result = await service.validate(response_text="")
        assert result.passed is False
        assert result.processing_time_ms == 0.0

    @pytest.mark.asyncio
    async def test_evidence_pipeline_error_propagation(self):
        """Evidence pipeline errors are captured in ServiceResult."""
        service = EvidenceService(pipeline=MockBrokenEvidencePipeline())
        result = await service.validate_evidence([make_evidence_span()])
        assert result.passed is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_safety_pipeline_error_propagation(self):
        """Safety pipeline errors are captured in SafetyServiceResult."""
        service = ClinicalSafetyService(pipeline=MockBrokenSafetyPipeline())
        result = await service.validate(response_text="Test.")
        assert result.passed is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_end_to_end_query_analyze_safety(self):
        """Partial end-to-end: simulate query -> analyze -> safety validate."""
        safety_service = ClinicalSafetyService(pipeline=make_safety_pipeline())

        simulated_query = "What are the symptoms of diabetes?"
        simulated_intent = "disease_information"
        simulated_entities = ["diabetes", "symptoms"]

        safety_result = await safety_service.validate(
            response_text=f"Query: {simulated_query} | Intent: {simulated_intent}",
            claims=[f"Query about {e}" for e in simulated_entities],
        )
        assert isinstance(safety_result, SafetyServiceResult)
        assert safety_result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_evidence_low_coverage_rejected(self):
        """Evidence with low coverage score is rejected."""
        low_coverage = CoverageResult(
            total_spans=1, verified_spans=0, coverage_score=0.1, evidence_density=0.0,
        )
        pipeline = make_evidence_pipeline(
            coverage_analyzer=MockCoverageAnalyzer(coverage_result=low_coverage),
        )
        config = EvidenceConfig(EVIDENCE_COVERAGE_MIN_SCORE=0.3)
        service = EvidenceService(pipeline=pipeline, config=config)
        result = await service.validate_evidence([make_evidence_span()])
        assert result.passed is False
        assert any("coverage below minimum" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_safety_low_confidence_rejected(self):
        """Safety pipeline with failing compliance rejects."""
        pipeline = make_safety_pipeline(
            compliance_validator=MockComplianceValidator(passed=False),
            approval_engine=MockApprovalEngine(decision=ApprovalDecision.REJECT),
        )
        service = ClinicalSafetyService(pipeline=pipeline)
        result = await service.validate(
            response_text="Aspirin cures all diseases.",
            claims=["Aspirin cures all diseases"],
        )
        assert result.passed is False


class TestMockProviderConsistency:
    """Verify that mock providers return deterministic results."""

    @pytest.mark.asyncio
    async def test_mock_llm_deterministic_response(self):
        """MockLLMProvider returns the same response for every call."""
        provider = MockLLMProvider(response="Fixed response")
        r1 = await provider.generate([{"role": "user", "content": "Hi"}])
        r2 = await provider.generate([{"role": "user", "content": "Completely different input"}])
        assert r1.content == r2.content == "Fixed response"

    @pytest.mark.asyncio
    async def test_mock_llm_async_deterministic(self):
        """MockLLMProvider async generate is deterministic."""
        provider = MockLLMProvider(response="Deterministic output")
        r1 = await provider.generate([{"role": "user", "content": "Hello"}])
        r2 = await provider.generate([{"role": "user", "content": "World"}])
        assert r1.content == r2.content == "Deterministic output"

    @pytest.mark.asyncio
    async def test_mock_llm_response_shape(self):
        """MockLLMProvider returns a proper CompletionResponse."""
        provider = MockLLMProvider(response="Test response", model="test-model")
        result = await provider.generate([{"role": "user", "content": "Hi"}])
        assert isinstance(result, CompletionResponse)
        assert result.content == "Test response"
        assert result.model == "test-model"
        assert result.provider == "mock"
        assert result.usage["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_mock_llm_model_info(self):
        """MockLLMProvider returns model info."""
        provider = MockLLMProvider(model="custom-model")
        info = await provider.get_model_info()
        assert info.name == "custom-model"
        assert info.provider == "mock"
        assert info.context_window == 4096

    @pytest.mark.asyncio
    async def test_mock_llm_token_count(self):
        """MockLLMProvider returns deterministic token count."""
        provider = MockLLMProvider()
        count = await provider.count_tokens([{"role": "user", "content": "Hi"}])
        assert count == 10

    @pytest.mark.asyncio
    async def test_mock_llm_stream(self):
        """MockLLMProvider streams words from its response."""
        provider = MockLLMProvider(response="hello world test")
        words = []
        async for chunk in provider.generate_stream([{"role": "user", "content": "Hi"}]):
            words.append(chunk)
        assert len(words) == 3
        assert "".join(words) == "hello world test "

    @pytest.mark.asyncio
    async def test_mock_embedding_deterministic(self):
        """MockEmbeddingProvider returns deterministic vectors for same input."""
        provider = MockEmbeddingProvider(dimension=4)
        v1 = await provider.embed(["headache"])
        v2 = await provider.embed(["headache"])
        assert v1[0] == v2[0]

    @pytest.mark.asyncio
    async def test_mock_embedding_dimension(self):
        """MockEmbeddingProvider returns vectors of correct dimension."""
        provider = MockEmbeddingProvider(dimension=384)
        vecs = await provider.embed(["test"])
        assert len(vecs) == 1
        assert len(vecs[0]) == 384

    @pytest.mark.asyncio
    async def test_mock_embedding_different_inputs_different_vectors(self):
        """MockEmbeddingProvider returns different vectors for different inputs."""
        provider = MockEmbeddingProvider(dimension=8)
        v1 = (await provider.embed(["headache"]))[0]
        v2 = (await provider.embed(["stomach ache"]))[0]
        assert v1 != v2

    @pytest.mark.asyncio
    async def test_mock_embedding_normalized(self):
        """MockEmbeddingProvider returns L2-normalized vectors."""
        provider = MockEmbeddingProvider(dimension=32)
        vecs = await provider.embed(["test"])
        magnitude = sum(v * v for v in vecs[0]) ** 0.5
        assert abs(magnitude - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_mock_embedding_deterministic_batch(self):
        """Batch embedding is deterministic."""
        provider = MockEmbeddingProvider(dimension=8)
        texts = ["a", "b", "c"]
        r1 = await provider.embed(texts)
        r2 = await provider.embed(texts)
        for v1, v2 in zip(r1, r2):
            assert v1 == v2

    def test_mock_embedding_provider_type(self):
        """MockEmbeddingProvider returns MOCK type."""
        provider = MockEmbeddingProvider()
        assert provider.provider_type().value == "mock"

    def test_mock_embedding_default_model(self):
        """MockEmbeddingProvider has a default model name."""
        provider = MockEmbeddingProvider()
        assert provider.default_model() == "mock-embedding-v1"

    def test_mock_embedding_supported_models(self):
        """MockEmbeddingProvider lists supported models."""
        provider = MockEmbeddingProvider()
        models = provider.supported_models()
        assert "mock-embedding-v1" in models
        assert "mock-large-v2" in models

    def test_mock_embedding_dimensions(self):
        """MockEmbeddingProvider reports correct dimensions."""
        provider = MockEmbeddingProvider(dimension=128)
        assert provider.dimensions() == 128

    def test_mock_llm_custom_constructor(self):
        """MockLLMProvider accepts custom response and model."""
        p1 = MockLLMProvider(response="R1", model="m1")
        p2 = MockLLMProvider(response="R2", model="m2")
        assert p1._response == "R1"
        assert p1._model == "m1"
        assert p2._response == "R2"
        assert p2._model == "m2"

    @pytest.mark.asyncio
    async def test_mock_llm_defaults(self):
        """MockLLMProvider uses sensible defaults."""
        provider = MockLLMProvider()
        result = await provider.generate([])
        assert result.content == "Mock response"
        assert result.model == "mock-model"
