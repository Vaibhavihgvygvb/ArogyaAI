import pytest

from app.ai.clinical_safety.services.approval import DefaultSafetyApprovalEngine
from app.ai.clinical_safety.schemas import (
    ApprovalDecision,
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
    RiskLevel,
    UnsupportedClaim,
    UnsupportedClaimReport,
    SupportLevel,
)


def _clean_hallucination_report() -> HallucinationReport:
    return HallucinationReport(
        results=[
            HallucinationResult(
                claim="Patient has a cold",
                hallucination_type=HallucinationType.UNKNOWN,
                confidence=0.0,
            )
        ],
        total_claims=1,
        hallucinated_count=0,
        hallucination_rate=0.0,
        passed=True,
    )


def _clean_unsupported_report() -> UnsupportedClaimReport:
    return UnsupportedClaimReport(
        claims=[
            UnsupportedClaim(
                claim="Patient has a cold",
                support_level=SupportLevel.FULLY_SUPPORTED,
                confidence=0.9,
            )
        ],
        total_claims=1,
        supported_count=1,
        unsupported_count=0,
        contradictory_count=0,
        coverage_score=1.0,
        passed=True,
    )


def _low_risk_report() -> ClinicalRiskReport:
    return ClinicalRiskReport(
        results=[
            ClinicalRiskResult(
                risk_level=RiskLevel.LOW, score=0.1
            )
        ],
        overall_risk=RiskLevel.LOW,
        max_risk_score=0.1,
        passed=True,
    )


def _clean_compliance_report() -> ComplianceReport:
    return ComplianceReport(
        checks=[
            ComplianceCheck(
                check_name="Hallucination Check", passed=True
            ),
            ComplianceCheck(
                check_name="Unsupported Claims Check", passed=True
            ),
            ComplianceCheck(check_name="Evidence Threshold", passed=True),
            ComplianceCheck(check_name="Disclaimer Present", passed=True),
            ComplianceCheck(
                check_name="No Prohibited Claims", passed=True
            ),
            ComplianceCheck(
                check_name="No Absolute Guarantees", passed=True
            ),
            ComplianceCheck(check_name="Citation Coverage", passed=True),
        ],
        total_checks=7,
        passed_checks=7,
        failed_checks=0,
        passed=True,
    )


def _clean_disclaimer_result() -> DisclaimerResult:
    return DisclaimerResult(
        selected_disclaimers=[
            DisclaimerConfig(
                disclaimer_type=DisclaimerType.GENERAL_MEDICAL,
                text="General medical disclaimer",
            )
        ],
    )


@pytest.mark.asyncio
async def test_all_clean_approved():
    engine = DefaultSafetyApprovalEngine()
    result = await engine.approve(
        hallucination_report=_clean_hallucination_report(),
        unsupported_report=_clean_unsupported_report(),
        risk_report=_low_risk_report(),
        compliance_report=_clean_compliance_report(),
        disclaimer_result=_clean_disclaimer_result(),
    )
    assert result.decision == ApprovalDecision.APPROVED


@pytest.mark.asyncio
async def test_high_hallucination_rate_reject():
    engine = DefaultSafetyApprovalEngine()
    hall_report = HallucinationReport(
        results=[
            HallucinationResult(
                claim="Fabricated claim",
                hallucination_type=HallucinationType.FABRICATED_STATISTIC,
                confidence=0.9,
            )
        ],
        total_claims=10,
        hallucinated_count=4,
        hallucination_rate=0.4,
        passed=False,
    )
    result = await engine.approve(
        hallucination_report=hall_report,
        unsupported_report=_clean_unsupported_report(),
        risk_report=_low_risk_report(),
        compliance_report=_clean_compliance_report(),
        disclaimer_result=_clean_disclaimer_result(),
    )
    assert result.decision == ApprovalDecision.REJECT


@pytest.mark.asyncio
async def test_critical_hallucination_reject():
    engine = DefaultSafetyApprovalEngine()
    hall_report = HallucinationReport(
        results=[
            HallucinationResult(
                claim="Take Drug X for diabetes",
                hallucination_type=HallucinationType.FABRICATED_MEDICATION,
                confidence=0.9,
            )
        ],
        total_claims=1,
        hallucinated_count=1,
        hallucination_rate=0.1,
        passed=False,
    )
    result = await engine.approve(
        hallucination_report=hall_report,
        unsupported_report=_clean_unsupported_report(),
        risk_report=_low_risk_report(),
        compliance_report=_clean_compliance_report(),
        disclaimer_result=_clean_disclaimer_result(),
    )
    assert result.decision == ApprovalDecision.REJECT


@pytest.mark.asyncio
async def test_critical_risk_escalate():
    engine = DefaultSafetyApprovalEngine()
    risk_report = ClinicalRiskReport(
        results=[
            ClinicalRiskResult(
                risk_level=RiskLevel.CRITICAL, score=0.95
            )
        ],
        overall_risk=RiskLevel.CRITICAL,
        max_risk_score=0.95,
        passed=False,
    )
    result = await engine.approve(
        hallucination_report=_clean_hallucination_report(),
        unsupported_report=_clean_unsupported_report(),
        risk_report=risk_report,
        compliance_report=_clean_compliance_report(),
        disclaimer_result=_clean_disclaimer_result(),
    )
    assert result.decision == ApprovalDecision.ESCALATE


@pytest.mark.asyncio
async def test_emergency_requires_override_escalate():
    engine = DefaultSafetyApprovalEngine()
    emergency_report = EmergencyReport(
        has_emergency=True,
        requires_override=True,
        results=[
            EmergencyResult(
                is_emergency=True,
                severity="high",
                indicators=["chest pain"],
            )
        ],
    )
    risk_report = ClinicalRiskReport(
        results=[
            ClinicalRiskResult(
                risk_level=RiskLevel.MODERATE, score=0.4
            )
        ],
        overall_risk=RiskLevel.MODERATE,
        max_risk_score=0.4,
        passed=True,
    )
    result = await engine.approve(
        hallucination_report=_clean_hallucination_report(),
        unsupported_report=_clean_unsupported_report(),
        risk_report=risk_report,
        compliance_report=_clean_compliance_report(),
        disclaimer_result=_clean_disclaimer_result(),
        emergency_report=emergency_report,
    )
    assert result.decision == ApprovalDecision.ESCALATE


@pytest.mark.asyncio
async def test_high_unsupported_rate_escalate():
    engine = DefaultSafetyApprovalEngine()
    unsup_report = UnsupportedClaimReport(
        claims=[
            UnsupportedClaim(
                claim="Claim without support",
                support_level=SupportLevel.UNSUPPORTED,
                confidence=0.9,
            )
        ],
        total_claims=10,
        supported_count=4,
        unsupported_count=6,
        contradictory_count=0,
        coverage_score=0.4,
        passed=False,
    )
    result = await engine.approve(
        hallucination_report=_clean_hallucination_report(),
        unsupported_report=unsup_report,
        risk_report=_low_risk_report(),
        compliance_report=_clean_compliance_report(),
        disclaimer_result=_clean_disclaimer_result(),
    )
    assert result.decision == ApprovalDecision.ESCALATE


@pytest.mark.asyncio
async def test_high_risk_approved_with_warnings():
    engine = DefaultSafetyApprovalEngine()
    risk_report = ClinicalRiskReport(
        results=[
            ClinicalRiskResult(
                risk_level=RiskLevel.HIGH, score=0.7
            )
        ],
        overall_risk=RiskLevel.HIGH,
        max_risk_score=0.7,
        passed=False,
    )
    result = await engine.approve(
        hallucination_report=_clean_hallucination_report(),
        unsupported_report=_clean_unsupported_report(),
        risk_report=risk_report,
        compliance_report=_clean_compliance_report(),
        disclaimer_result=_clean_disclaimer_result(),
    )
    assert result.decision == ApprovalDecision.APPROVED_WITH_WARNINGS


@pytest.mark.asyncio
async def test_moderate_hallucinations_approved_with_warnings():
    engine = DefaultSafetyApprovalEngine()
    hall_report = HallucinationReport(
        results=[
            HallucinationResult(
                claim="Possibly fabricated claim",
                hallucination_type=HallucinationType.FABRICATED_STATISTIC,
                confidence=0.7,
            )
        ],
        total_claims=20,
        hallucinated_count=3,
        hallucination_rate=0.15,
        passed=False,
    )
    result = await engine.approve(
        hallucination_report=hall_report,
        unsupported_report=_clean_unsupported_report(),
        risk_report=_low_risk_report(),
        compliance_report=_clean_compliance_report(),
        disclaimer_result=_clean_disclaimer_result(),
    )
    assert result.decision == ApprovalDecision.APPROVED_WITH_WARNINGS


@pytest.mark.asyncio
async def test_multiple_compliance_warnings_approved_with_warnings():
    engine = DefaultSafetyApprovalEngine()
    compliance_report = ComplianceReport(
        checks=[
            ComplianceCheck(
                check_name="Hallucination Check", passed=True
            ),
            ComplianceCheck(
                check_name="Disclaimer Present", passed=False
            ),
            ComplianceCheck(
                check_name="Evidence Threshold", passed=True
            ),
            ComplianceCheck(
                check_name="Citation Coverage", passed=True
            ),
            ComplianceCheck(
                check_name="No Absolute Guarantees", passed=True
            ),
            ComplianceCheck(
                check_name="No Prohibited Claims", passed=True
            ),
            ComplianceCheck(
                check_name="Unsupported Claims Check", passed=True
            ),
        ],
        total_checks=7,
        passed_checks=6,
        failed_checks=1,
        passed=False,
    )
    risk_report = ClinicalRiskReport(
        results=[
            ClinicalRiskResult(
                risk_level=RiskLevel.HIGH, score=0.7
            )
        ],
        overall_risk=RiskLevel.HIGH,
        max_risk_score=0.7,
        passed=False,
    )
    result = await engine.approve(
        hallucination_report=_clean_hallucination_report(),
        unsupported_report=_clean_unsupported_report(),
        risk_report=risk_report,
        compliance_report=compliance_report,
        disclaimer_result=_clean_disclaimer_result(),
    )
    assert result.decision == ApprovalDecision.APPROVED_WITH_WARNINGS


@pytest.mark.asyncio
async def test_approval_reasons_list_populated():
    engine = DefaultSafetyApprovalEngine()
    result = await engine.approve(
        hallucination_report=_clean_hallucination_report(),
        unsupported_report=_clean_unsupported_report(),
        risk_report=_low_risk_report(),
        compliance_report=_clean_compliance_report(),
        disclaimer_result=_clean_disclaimer_result(),
    )
    assert len(result.reasons) > 0


@pytest.mark.asyncio
async def test_requires_escalation_flag():
    engine = DefaultSafetyApprovalEngine()
    risk_report = ClinicalRiskReport(
        results=[
            ClinicalRiskResult(
                risk_level=RiskLevel.CRITICAL, score=0.95
            )
        ],
        overall_risk=RiskLevel.CRITICAL,
        max_risk_score=0.95,
        passed=False,
    )
    result = await engine.approve(
        hallucination_report=_clean_hallucination_report(),
        unsupported_report=_clean_unsupported_report(),
        risk_report=risk_report,
        compliance_report=_clean_compliance_report(),
        disclaimer_result=_clean_disclaimer_result(),
    )
    assert result.requires_escalation is True


@pytest.mark.asyncio
async def test_low_hallucination_low_risk_approved():
    engine = DefaultSafetyApprovalEngine()
    hall_report = HallucinationReport(
        results=[
            HallucinationResult(
                claim="Patient has a mild headache",
                hallucination_type=HallucinationType.UNKNOWN,
                confidence=0.0,
            )
        ],
        total_claims=10,
        hallucinated_count=0,
        hallucination_rate=0.05,
        passed=True,
    )
    result = await engine.approve(
        hallucination_report=hall_report,
        unsupported_report=_clean_unsupported_report(),
        risk_report=_low_risk_report(),
        compliance_report=_clean_compliance_report(),
        disclaimer_result=_clean_disclaimer_result(),
    )
    assert result.decision == ApprovalDecision.APPROVED


@pytest.mark.asyncio
async def test_summary_populated_with_decision():
    engine = DefaultSafetyApprovalEngine()
    result = await engine.approve(
        hallucination_report=_clean_hallucination_report(),
        unsupported_report=_clean_unsupported_report(),
        risk_report=_low_risk_report(),
        compliance_report=_clean_compliance_report(),
        disclaimer_result=_clean_disclaimer_result(),
    )
    assert result.summary is not None
    assert "approved" in result.summary.lower()
