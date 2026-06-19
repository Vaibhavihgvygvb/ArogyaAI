import pytest

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
    PipelineResult,
    RiskLevel,
    SafetyServiceResult,
    SafetyState,
    SupportLevel,
    UnsupportedClaim,
    UnsupportedClaimReport,
)
from app.ai.clinical_safety.services._service import ClinicalSafetyService


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


class MockBrokenPipeline:
    async def run(self, text, claims=None, evidence=None, config_override=None):
        raise RuntimeError("Pipeline crashed")


def make_pipeline(**engine_overrides):
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


class TestClinicalSafetyService:
    @pytest.mark.asyncio
    async def test_validate_empty_text_returns_passed_false(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.validate(response_text="")

        assert result.passed is False
        assert "No response text provided." in result.summary
        assert result.processing_time_ms == 0.0

    @pytest.mark.asyncio
    async def test_validate_clean_text_returns_passed_true(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.validate(response_text="Take aspirin daily for heart health.")

        assert result.passed is True
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_validate_with_hallucinated_text(self):
        pipeline = make_pipeline(
            hallucination_detector=MockHallucinationDetector(hallucination_rate=0.8),
            approval_engine=MockApprovalEngine(decision=ApprovalDecision.REJECT),
        )
        service = ClinicalSafetyService(pipeline=pipeline)
        result = await service.validate(
            response_text="A new drug Xylomab reduces heart attack risk by 100%."
        )

        assert result.passed is False

    @pytest.mark.asyncio
    async def test_validate_with_emergency_text_passes_but_has_warning(self):
        pipeline = make_pipeline(
            emergency_detector=MockEmergencyDetector(has_emergency=True, severity="high"),
            approval_engine=MockApprovalEngine(decision=ApprovalDecision.ESCALATE),
        )
        service = ClinicalSafetyService(pipeline=pipeline)
        result = await service.validate(
            response_text="Patient is experiencing chest pain and shortness of breath."
        )

        assert isinstance(result, SafetyServiceResult)
        assert any("Emergency detected" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_detect_hallucinations_returns_report(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.detect_hallucinations(
            text="Aspirin cures cancer.",
            claims=["Aspirin cures cancer"],
        )
        assert isinstance(result, HallucinationReport)

    @pytest.mark.asyncio
    async def test_detect_unsupported_claims_returns_report(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.detect_unsupported_claims(
            claims=["Aspirin reduces heart attack risk"],
            evidence={"Aspirin reduces heart attack risk": "true"},
        )
        assert isinstance(result, UnsupportedClaimReport)

    @pytest.mark.asyncio
    async def test_assess_risk_returns_report(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.assess_risk(
            text="Aspirin reduces heart attack risk.",
            claims=["Aspirin reduces heart attack risk"],
        )
        assert isinstance(result, ClinicalRiskReport)

    @pytest.mark.asyncio
    async def test_detect_emergency_returns_report(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.detect_emergency(
            text="Patient is experiencing chest pain.",
            claims=["chest pain"],
        )
        assert isinstance(result, EmergencyReport)

    @pytest.mark.asyncio
    async def test_validate_phi_returns_report(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.validate_phi(text="Patient SSN is 123-45-6789.")
        assert isinstance(result, PHIValidationReport)

    @pytest.mark.asyncio
    async def test_select_disclaimer_returns_result(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.select_disclaimer(
            text="Take aspirin daily.",
            claims=["Take aspirin daily"],
        )
        assert isinstance(result, DisclaimerResult)

    @pytest.mark.asyncio
    async def test_validate_compliance_returns_report(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.validate_compliance(
            text="Aspirin reduces heart attack risk.",
            claims=["Aspirin reduces heart attack risk"],
        )
        assert isinstance(result, ComplianceReport)

    @pytest.mark.asyncio
    async def test_get_approval_returns_result(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.get_approval(
            text="Aspirin reduces heart attack risk.",
            claims=["Aspirin reduces heart attack risk"],
        )
        assert isinstance(result, ApprovalResult)

    @pytest.mark.asyncio
    async def test_summary_includes_key_info(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.validate(response_text="Aspirin reduces heart attack risk.")
        assert "Hallucination rate" in result.summary or "Risk" in result.summary
        assert result.summary is not None

    @pytest.mark.asyncio
    async def test_warnings_populated_for_issues(self):
        pipeline = make_pipeline(
            emergency_detector=MockEmergencyDetector(has_emergency=True, severity="critical"),
        )
        service = ClinicalSafetyService(pipeline=pipeline)
        result = await service.validate(response_text="Patient is having a heart attack.")
        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_errors_populated_on_failure(self):
        service = ClinicalSafetyService(pipeline=MockBrokenPipeline())
        result = await service.validate(response_text="Test.")
        assert result.passed is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_validate_returns_safety_service_result(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.validate(response_text="Aspirin reduces heart attack risk.")
        assert isinstance(result, SafetyServiceResult)

    @pytest.mark.asyncio
    async def test_approval_included_in_validate_result(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.validate(response_text="Aspirin reduces heart attack risk.")
        assert result.approval is not None
        assert result.approval.decision == ApprovalDecision.APPROVED

    @pytest.mark.asyncio
    async def test_empty_whitespace_text_returns_passed_false(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.validate(response_text="   ")
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_processing_time_tracked(self):
        service = ClinicalSafetyService(pipeline=make_pipeline())
        result = await service.validate(response_text="Aspirin reduces heart attack risk.")
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_default_pipeline_created_when_none_given(self):
        service = ClinicalSafetyService()
        assert service._pipeline is not None
        assert isinstance(service._pipeline, ClinicalSafetyPipeline)
