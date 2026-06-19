import pytest
from datetime import datetime
from uuid import uuid4

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
from app.ai.clinical_safety.services.compliance import DefaultComplianceValidator
from app.ai.clinical_safety.services.approval import DefaultSafetyApprovalEngine
from app.ai.evidence.config import EvidenceConfig
from app.ai.evidence.pipeline import EvidencePipeline
from app.ai.evidence.schemas import (
    Citation,
    CitationGroup,
    CitationStyle,
    ConfidenceBreakdown,
    ConfidenceResult,
    ConflictResult,
    ConflictType,
    CoverageResult,
    EvidenceSpan,
    EvidenceState,
    ExplanationComponent,
    ExplanationResult,
    FormattedCitation,
    PipelineResult as EvidencePipelineResult,
    ServiceResult,
    VerificationResult,
    VerificationStatus,
    VerifiedSource,
)
from app.ai.evidence.service import EvidenceService
from app.ai.evaluation.runner import EvaluationRunner
from app.ai.evaluation.reporter import ReportGenerator
from app.ai.evaluation.schemas import EvaluationMetric, EvaluationRun, MetricCategory


# ---------------------------------------------------------------------------
# Mock engines for EvidencePipeline
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
        return [
            CitationGroup(claim=c.evidence_text, citations=[c], total_citations=1)
            for c in citations
        ]


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
        self, verification_results, coverage=None, conflicts=None, confidence=None, citations=None, state=None
    ):
        return ExplanationResult(summary="Analysis complete.")


class MockBrokenPipeline:
    async def run(self, spans, citation_style=CitationStyle.AMA, config_override=None):
        raise RuntimeError("Pipeline crashed")


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
        config=None,
    )
    defaults.update(engine_overrides)
    return EvidencePipeline(**defaults)


def make_span(claim="Aspirin reduces heart attack risk", text=None):
    if text is None:
        text = claim
    return EvidenceSpan(text=text, claim=claim, span_start=0, span_end=len(text))


# ---------------------------------------------------------------------------
# Mock engines for ClinicalSafetyPipeline
# ---------------------------------------------------------------------------

class MockHallucinationDetector:
    def __init__(self, hallucination_rate=0.0):
        self._rate = hallucination_rate

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
            total_claims=len(claims) if claims else 1 if has_hallu else 0,
            hallucinated_count=1 if has_hallu else 0,
            hallucination_rate=self._rate,
            passed=self._rate < 0.5,
            summary=f"Mock: rate {self._rate:.0%}.",
        )

    def _extract_claims(self, text):
        return [s.strip() for s in text.split(".") if len(s.strip()) > 5][:100]


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

    async def validate(self, hallucination_report, unsupported_report, disclaimer_result, risk_report=None):
        return ComplianceReport(
            checks=[
                ComplianceCheck(check_name="Hallucination Check", passed=self._passed, severity="high"),
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

    async def approve(self, hallucination_report, unsupported_report, risk_report, compliance_report, disclaimer_result, emergency_report=None):
        return ApprovalResult(
            decision=self._decision,
            reasons=["Mock approval."],
            warnings=[] if self._decision == ApprovalDecision.APPROVED else ["Warning: high risk"],
            requires_escalation=self._decision == ApprovalDecision.ESCALATE,
            requires_override=self._decision == ApprovalDecision.REJECT,
            summary=f"Mock: {self._decision.value}.",
        )


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


# ===================================================================
# TestHappyPaths
# ===================================================================

class TestHappyPaths:

    @pytest.mark.asyncio
    async def test_clean_response_passes_safety(self):
        service = ClinicalSafetyService(pipeline=make_safety_pipeline())
        result = await service.validate(response_text="Aspirin is used for pain relief.")

        assert result.passed is True
        assert result.processing_time_ms > 0
        assert result.approval is not None
        assert result.approval.decision == ApprovalDecision.APPROVED

    @pytest.mark.asyncio
    async def test_valid_evidence_passes_validation(self):
        service = EvidenceService(pipeline=make_evidence_pipeline())
        spans = [
            EvidenceSpan(
                text="Aspirin is an NSAID used for pain relief.",
                claim="Aspirin is an NSAID",
                span_start=0,
                span_end=46,
            )
        ]
        result = await service.validate_evidence(spans)

        assert result.passed is True
        assert result.processing_time_ms > 0
        assert result.pipeline_result is not None

    def test_evaluation_run_created(self):
        runner = EvaluationRunner()
        metrics = [
            EvaluationMetric(
                name="evidence_coverage",
                category=MetricCategory.EVIDENCE,
                value=0.95,
                weight=1.0,
                passed=True,
            ),
            EvaluationMetric(
                name="safety_approval_rate",
                category=MetricCategory.SAFETY,
                value=1.0,
                weight=1.0,
                passed=True,
            ),
        ]
        run = runner.create_run(pipeline_name="test_pipeline", metrics=metrics)

        assert run.id is not None
        assert run.pipeline_name == "test_pipeline"
        assert len(run.metrics) == 2
        assert run.summary_score > 0
        assert run.passed is True


# ===================================================================
# TestInvalidInputs
# ===================================================================

class TestInvalidInputs:

    @pytest.mark.asyncio
    async def test_empty_evidence_returns_passed_true(self):
        service = EvidenceService(pipeline=make_evidence_pipeline())
        result = await service.validate_evidence([])

        assert result.passed is True
        assert result.summary == "No evidence spans to validate."
        assert result.processing_time_ms == 0.0

    @pytest.mark.asyncio
    async def test_empty_safety_response_returns_failed(self):
        service = ClinicalSafetyService(pipeline=make_safety_pipeline())
        result = await service.validate(response_text="")

        assert result.passed is False
        assert "No response text provided." in result.summary
        assert result.processing_time_ms == 0.0

    def test_evaluation_empty_metrics(self):
        runner = EvaluationRunner()
        run = runner.create_run(pipeline_name="metrics_test", metrics=[])

        assert run.summary_score == 0.0
        assert run.passed is False

    @pytest.mark.asyncio
    async def test_evidence_text_too_long(self):
        service = EvidenceService(pipeline=make_evidence_pipeline())
        long_text = "A" * 100_000
        spans = [EvidenceSpan(text=long_text, claim=long_text, span_start=0, span_end=len(long_text))]
        result = await service.validate_evidence(spans)

        assert result.passed is True
        assert result.processing_time_ms > 0


# ===================================================================
# TestEmergencyScenarios
# ===================================================================

class TestEmergencyScenarios:

    @pytest.mark.asyncio
    async def test_chest_pain_detected(self):
        from app.ai.clinical_safety.services.emergency import DefaultEmergencyDetector

        detector = DefaultEmergencyDetector()
        report = await detector.detect("Patient reports chest pain.", [])

        assert report.has_emergency is True
        assert len(report.results) == 1
        assert report.results[0].emergency_type == EmergencyType.CHEST_PAIN
        assert report.results[0].is_emergency is True
        assert report.results[0].confidence >= 0.9

    @pytest.mark.asyncio
    async def test_suicidal_ideation_detected(self):
        from app.ai.clinical_safety.services.emergency import DefaultEmergencyDetector

        detector = DefaultEmergencyDetector()
        report = await detector.detect("I want to die.", [])

        assert report.has_emergency is True
        assert report.results[0].emergency_type == EmergencyType.SUICIDAL_IDEATION
        assert report.results[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_multiple_emergencies(self):
        from app.ai.clinical_safety.services.emergency import DefaultEmergencyDetector

        detector = DefaultEmergencyDetector()
        report = await detector.detect(
            "Patient has chest pain and difficulty breathing.", []
        )

        assert report.has_emergency is True
        assert len(report.results) >= 2
        detected_types = {r.emergency_type for r in report.results}
        assert EmergencyType.CHEST_PAIN in detected_types
        assert EmergencyType.RESPIRATORY_DISTRESS in detected_types

    @pytest.mark.asyncio
    async def test_emergency_overrides_approval(self):
        pipeline = make_safety_pipeline(
            emergency_detector=MockEmergencyDetector(has_emergency=True, severity="critical"),
            approval_engine=MockApprovalEngine(decision=ApprovalDecision.ESCALATE),
        )
        service = ClinicalSafetyService(pipeline=pipeline)
        result = await service.validate(
            response_text="Patient is having a heart attack."
        )

        assert any("Emergency detected" in w for w in result.warnings)
        assert result.approval.requires_escalation is True


# ===================================================================
# TestComplianceFailures
# ===================================================================

class TestComplianceFailures:

    @pytest.mark.asyncio
    async def test_prohibited_terms_caught(self):
        validator = DefaultComplianceValidator()
        hall_report = HallucinationReport(
            results=[
                HallucinationResult(
                    claim="This treatment guarantees a cure for all diseases.",
                    hallucination_type=HallucinationType.UNSUPPORTED_CLAIM,
                    confidence=0.9,
                )
            ],
            total_claims=1,
            hallucinated_count=0,
            hallucination_rate=0.0,
            passed=True,
        )
        unsup_report = UnsupportedClaimReport(
            claims=[], total_claims=0, supported_count=0,
            unsupported_count=0, contradictory_count=0,
            coverage_score=1.0, passed=True,
        )
        disc_result = DisclaimerResult(
            selected_disclaimers=[
                DisclaimerConfig(
                    disclaimer_type=DisclaimerType.GENERAL_MEDICAL,
                    text="General medical disclaimer",
                )
            ],
        )

        report = await validator.validate(
            hallucination_report=hall_report,
            unsupported_report=unsup_report,
            disclaimer_result=disc_result,
        )
        prohibited_check = next(
            c for c in report.checks if c.check_name == "No Prohibited Claims"
        )
        assert prohibited_check.passed is False
        assert report.passed is False

    @pytest.mark.asyncio
    async def test_absolute_guarantees_caught(self):
        validator = DefaultComplianceValidator()
        hall_report = HallucinationReport(
            results=[
                HallucinationResult(
                    claim="This is 100% effective for all patients.",
                    hallucination_type=HallucinationType.UNSUPPORTED_CLAIM,
                    confidence=0.9,
                )
            ],
            total_claims=1,
            hallucinated_count=0,
            hallucination_rate=0.0,
            passed=True,
        )
        unsup_report = UnsupportedClaimReport(
            claims=[], total_claims=0, supported_count=0,
            unsupported_count=0, contradictory_count=0,
            coverage_score=1.0, passed=True,
        )
        disc_result = DisclaimerResult(
            selected_disclaimers=[
                DisclaimerConfig(
                    disclaimer_type=DisclaimerType.GENERAL_MEDICAL,
                    text="General medical disclaimer",
                )
            ],
        )

        report = await validator.validate(
            hallucination_report=hall_report,
            unsupported_report=unsup_report,
            disclaimer_result=disc_result,
        )
        guarantee_check = next(
            c for c in report.checks if c.check_name == "No Absolute Guarantees"
        )
        assert guarantee_check.passed is False
        assert report.passed is False

    @pytest.mark.asyncio
    async def test_hallucinated_content_rejected(self):
        pipeline = make_safety_pipeline(
            hallucination_detector=MockHallucinationDetector(hallucination_rate=0.8),
            approval_engine=MockApprovalEngine(decision=ApprovalDecision.REJECT),
        )
        service = ClinicalSafetyService(pipeline=pipeline)
        result = await service.validate(
            response_text="Xylomab is a new drug that cures all infections."
        )

        assert result.passed is False
        assert result.approval.decision == ApprovalDecision.REJECT


# ===================================================================
# TestLargeInputs
# ===================================================================

class TestLargeInputs:

    @pytest.mark.asyncio
    async def test_large_evidence_set(self):
        service = EvidenceService(pipeline=make_evidence_pipeline())
        spans = [
            EvidenceSpan(
                text=f"Medical claim number {i}.",
                claim=f"Claim {i} is a valid medical observation.",
                span_start=0,
                span_end=50,
            )
            for i in range(25)
        ]
        result = await service.validate_evidence(spans)

        assert result.passed is True
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_long_response_text(self):
        service = ClinicalSafetyService(pipeline=make_safety_pipeline())
        long_response = " ".join(["Aspirin is a common medication." for _ in range(200)])
        result = await service.validate(response_text=long_response)

        assert result.passed is True
        assert result.processing_time_ms > 0


# ===================================================================
# TestEvaluationFramework
# ===================================================================

class TestEvaluationFramework:

    def test_metrics_computed(self):
        runner = EvaluationRunner()
        metrics = [
            EvaluationMetric(
                name="retrieval_precision",
                category=MetricCategory.RETRIEVAL,
                value=0.85,
                weight=1.0,
                passed=True,
            ),
            EvaluationMetric(
                name="evidence_coverage",
                category=MetricCategory.EVIDENCE,
                value=0.72,
                weight=2.0,
                passed=True,
                details="Coverage above minimum threshold.",
            ),
            EvaluationMetric(
                name="pipeline_latency_ms",
                category=MetricCategory.LATENCY,
                value=340.0,
                weight=0.5,
                passed=True,
            ),
        ]
        run = runner.create_run(pipeline_name="regression_test", metrics=metrics)

        assert run.summary_score > 0
        assert run.passed is True
        assert len(run.metrics) == 3

    def test_run_comparison(self):
        runner = EvaluationRunner()
        run_a = runner.create_run(
            pipeline_name="compare_test",
            metrics=[
                EvaluationMetric(
                    name="evidence_coverage",
                    category=MetricCategory.EVIDENCE,
                    value=0.9,
                    weight=1.0,
                    passed=True,
                ),
                EvaluationMetric(
                    name="safety_approval_rate",
                    category=MetricCategory.SAFETY,
                    value=0.8,
                    weight=1.0,
                    passed=True,
                ),
            ],
        )
        run_b = runner.create_run(
            pipeline_name="compare_test",
            metrics=[
                EvaluationMetric(
                    name="evidence_coverage",
                    category=MetricCategory.EVIDENCE,
                    value=0.7,
                    weight=1.0,
                    passed=True,
                ),
                EvaluationMetric(
                    name="safety_approval_rate",
                    category=MetricCategory.SAFETY,
                    value=0.6,
                    weight=1.0,
                    passed=True,
                ),
            ],
        )
        comparison = runner.compare_runs([run_a.id, run_b.id])

        assert comparison["run_count"] == 2
        assert comparison["min_score"] < comparison["max_score"]
        assert comparison["score_delta"] > 0
        assert "metric_deltas" in comparison
        assert comparison["metric_deltas"]["evidence_coverage"] == pytest.approx(0.2)

    def test_report_generated(self):
        runner = EvaluationRunner()
        metrics = [
            EvaluationMetric(
                name="evidence_coverage",
                category=MetricCategory.EVIDENCE,
                value=0.88,
                weight=1.0,
                passed=True,
                details="All claims verified.",
            ),
        ]
        run = runner.create_run(pipeline_name="report_test", metrics=metrics)
        report = ReportGenerator.generate_text_report(run)

        assert "Run ID:" in report
        assert "report_test" in report
        assert "Summary Score:" in report
        assert "PASS" in report
        assert "evidence_coverage" in report
