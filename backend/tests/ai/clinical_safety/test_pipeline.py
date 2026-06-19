import pytest

from app.ai.clinical_safety.exceptions import SafetyPipelineError
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
    HallucinationReport,
    HallucinationResult,
    HallucinationType,
    PHIFinding,
    PHIValidationReport,
    PHIType,
    PipelineResult,
    RiskLevel,
    SafetyState,
    SupportLevel,
    UnsupportedClaim,
    UnsupportedClaimReport,
)


class MockHallucinationDetector:
    async def detect(self, text, claims, evidence=None):
        return HallucinationReport(
            results=[
                HallucinationResult(
                    claim=claims[0] if claims else "test",
                    hallucination_type=HallucinationType.UNKNOWN,
                    confidence=0.1,
                    details="Mock detection",
                )
            ],
            total_claims=len(claims) if claims else 1,
            hallucinated_count=0,
            hallucination_rate=0.0,
            passed=True,
            summary="Mock hallucination check.",
        )

    def _extract_claims(self, text):
        return [s.strip() for s in text.split(".") if len(s.strip()) > 5][:100]


class MockUnsupportedDetector:
    async def detect(self, claims, evidence=None):
        return UnsupportedClaimReport(
            claims=[
                UnsupportedClaim(
                    claim=c,
                    support_level=SupportLevel.FULLY_SUPPORTED,
                    confidence=0.9,
                    matched_evidence=["evidence"],
                    missing_evidence=[],
                )
                for c in claims
            ],
            total_claims=len(claims),
            supported_count=len(claims),
            unsupported_count=0,
            contradictory_count=0,
            coverage_score=1.0,
            passed=True,
            summary="Mock unsupported check.",
        )


class MockRiskEngine:
    async def assess(self, hallucination_report, unsupported_report, emergency_report=None):
        return ClinicalRiskReport(
            results=[
                ClinicalRiskResult(
                    risk_level=RiskLevel.LOW,
                    score=0.1,
                    factors=[],
                    confidence_impact=0.0,
                    unsupported_impact=0.0,
                    topic_sensitivity=0.0,
                    emergency_indicators=[],
                    details="Mock risk assessment.",
                )
            ],
            overall_risk=RiskLevel.LOW,
            max_risk_score=0.1,
            passed=True,
            summary="Mock risk: low.",
        )


class MockEmergencyDetector:
    async def detect(self, text, claims):
        return EmergencyReport(
            results=[],
            has_emergency=False,
            max_severity="none",
            requires_override=False,
            summary="No emergency detected.",
        )


class MockPHIValidator:
    async def validate(self, text):
        return PHIValidationReport(
            findings=[],
            total_findings=0,
            has_phi=False,
            passed=True,
            summary="No PHI detected.",
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
            has_emergency_disclaimer=False,
            has_medication_disclaimer=False,
            has_mental_health_disclaimer=False,
            summary="Selected 1 disclaimer(s).",
        )

    async def get_disclaimers(self):
        return []


class MockComplianceValidator:
    async def validate(self, hallucination_report, unsupported_report, disclaimer_result, risk_report=None):
        return ComplianceReport(
            checks=[
                ComplianceCheck(check_name="Hallucination Check", passed=True, severity="high"),
                ComplianceCheck(check_name="Unsupported Claims Check", passed=True, severity="high"),
                ComplianceCheck(check_name="Disclaimer Present", passed=True, severity="high"),
            ],
            total_checks=3,
            passed_checks=3,
            failed_checks=0,
            passed=True,
            summary="3/3 checks passed.",
        )


class MockApprovalEngine:
    async def approve(self, hallucination_report, unsupported_report, risk_report, compliance_report, disclaimer_result, emergency_report=None):
        return ApprovalResult(
            decision=ApprovalDecision.APPROVED,
            reasons=["All safety checks passed."],
            warnings=[],
            requires_escalation=False,
            requires_override=False,
            summary="Response approved.",
        )


class MockBrokenEngine:
    async def detect(self, *args, **kwargs):
        raise RuntimeError("Simulated engine failure")


def make_pipeline(**overrides):
    defaults = dict(
        hallucination_detector=MockHallucinationDetector(),
        unsupported_detector=MockUnsupportedDetector(),
        risk_engine=MockRiskEngine(),
        emergency_detector=MockEmergencyDetector(),
        phi_validator=MockPHIValidator(),
        disclaimer_engine=MockDisclaimerEngine(),
        compliance_validator=MockComplianceValidator(),
        approval_engine=MockApprovalEngine(),
        config=None,
    )
    defaults.update(overrides)
    return ClinicalSafetyPipeline(**defaults)


class TestClinicalSafetyPipeline:
    @pytest.mark.asyncio
    async def test_run_empty_text_processes_all_steps(self):
        pipeline = make_pipeline()
        result = await pipeline.run(text="")

        assert isinstance(result, PipelineResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_all_8_steps_in_steps_completed(self):
        pipeline = make_pipeline()
        result = await pipeline.run(text="Take aspirin daily for heart health.")

        expected_steps = [
            "hallucination",
            "emergency",
            "unsupported_claims",
            "risk_assessment",
            "phi_validation",
            "disclaimer",
            "compliance",
            "approval",
        ]
        for step in expected_steps:
            assert step in result.steps_completed, f"Missing step: {step}"
        assert result.steps_completed == expected_steps

    @pytest.mark.asyncio
    async def test_steps_listed_in_request(self):
        pipeline = make_pipeline()
        result = await pipeline.run(text="Test.")
        assert "hallucination" in result.steps_completed
        assert "emergency" in result.steps_completed
        assert "unsupported_claims" in result.steps_completed
        assert "risk_assessment" in result.steps_completed
        assert "phi_validation" in result.steps_completed
        assert "disclaimer" in result.steps_completed
        assert "compliance" in result.steps_completed
        assert "approval" in result.steps_completed

    @pytest.mark.asyncio
    async def test_pipeline_with_custom_claim_extraction(self):
        pipeline = make_pipeline()
        result = await pipeline.run(text="Aspirin reduces heart attack risk.")
        assert result.state.hallucination_report is not None
        assert result.state.unsupported_report is not None

    @pytest.mark.asyncio
    async def test_pipeline_with_provided_claims_list(self):
        pipeline = make_pipeline()
        claims = ["Aspirin prevents heart attacks", "Metformin treats diabetes"]
        result = await pipeline.run(text="Some text", claims=claims)

        assert result.state.claims == claims
        assert result.state.hallucination_report.total_claims == len(claims)

    @pytest.mark.asyncio
    async def test_pipeline_with_evidence_dict(self):
        pipeline = make_pipeline()
        evidence = {"Aspirin reduces heart attack risk": "true"}
        result = await pipeline.run(
            text="Aspirin reduces heart attack risk.",
            evidence=evidence,
        )
        assert result.state.hallucination_report is not None
        assert result.state.unsupported_report is not None

    @pytest.mark.asyncio
    async def test_state_populated_with_all_reports(self):
        pipeline = make_pipeline()
        result = await pipeline.run(text="Take aspirin daily for heart health.")

        assert isinstance(result.state, SafetyState)
        assert result.state.hallucination_report is not None
        assert result.state.unsupported_report is not None
        assert result.state.risk_report is not None
        assert result.state.emergency_report is not None
        assert result.state.phi_report is not None
        assert result.state.disclaimer_result is not None
        assert result.state.compliance_report is not None
        assert result.state.approval_result is not None

    @pytest.mark.asyncio
    async def test_total_processing_time_ms_gt_zero(self):
        pipeline = make_pipeline()
        result = await pipeline.run(text="Aspirin reduces heart attack risk.")
        assert result.total_processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_success_true_when_no_errors(self):
        pipeline = make_pipeline()
        result = await pipeline.run(text="Aspirin reduces heart attack risk.")
        assert result.success is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_pipeline_with_mock_engines_injected(self):
        hallu = MockHallucinationDetector()
        unsup = MockUnsupportedDetector()
        risk = MockRiskEngine()
        emergency = MockEmergencyDetector()
        phi = MockPHIValidator()
        disc = MockDisclaimerEngine()
        comp = MockComplianceValidator()
        approval = MockApprovalEngine()

        pipeline = ClinicalSafetyPipeline(
            hallucination_detector=hallu,
            unsupported_detector=unsup,
            risk_engine=risk,
            emergency_detector=emergency,
            phi_validator=phi,
            disclaimer_engine=disc,
            compliance_validator=comp,
            approval_engine=approval,
        )
        result = await pipeline.run(text="Aspirin reduces heart attack risk.")
        assert result.success is True
        assert result.state.hallucination_report is not None
        assert result.state.approval_result is not None

    @pytest.mark.asyncio
    async def test_error_handling_broken_engine(self):
        pipeline = make_pipeline(hallucination_detector=MockBrokenEngine())
        with pytest.raises(SafetyPipelineError):
            await pipeline.run(text="Aspirin reduces heart attack risk.")

    @pytest.mark.asyncio
    async def test_default_engine_creation(self):
        pipeline = ClinicalSafetyPipeline()
        assert pipeline._hallucination_detector is not None
        assert pipeline._unsupported_detector is not None
        assert pipeline._risk_engine is not None
        assert pipeline._emergency_detector is not None
        assert pipeline._phi_validator is not None
        assert pipeline._disclaimer_engine is not None
        assert pipeline._compliance_validator is not None
        assert pipeline._approval_engine is not None
        assert pipeline._config is not None

    @pytest.mark.asyncio
    async def test_pipeline_name_in_result(self):
        pipeline = make_pipeline()
        result = await pipeline.run(text="Test.")
        assert result.pipeline_name == "clinical_safety"

    @pytest.mark.asyncio
    async def test_config_override_populates_state(self):
        pipeline = make_pipeline()
        result = await pipeline.run(text="Test.", config_override={"custom": "value"})
        assert result.state.config.get("custom") == "value"

    @pytest.mark.asyncio
    async def test_no_steps_skipped_when_all_succeed(self):
        pipeline = make_pipeline()
        result = await pipeline.run(text="Test.")
        assert len(result.steps_skipped) == 0

    @pytest.mark.asyncio
    async def test_no_claims_does_not_crash(self):
        pipeline = make_pipeline()
        result = await pipeline.run(text="")
        assert result.success is True
