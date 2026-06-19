import pytest

from app.ai.clinical_safety.services.compliance import DefaultComplianceValidator
from app.ai.clinical_safety.schemas import (
    ClinicalRiskReport,
    ClinicalRiskResult,
    ComplianceReport,
    DisclaimerConfig,
    DisclaimerResult,
    DisclaimerType,
    HallucinationReport,
    HallucinationResult,
    HallucinationType,
    UnsupportedClaim,
    UnsupportedClaimReport,
    SupportLevel,
)


def _make_clean_hallucination_report() -> HallucinationReport:
    return HallucinationReport(
        results=[
            HallucinationResult(
                claim="Patient has diabetes",
                hallucination_type=HallucinationType.UNKNOWN,
                confidence=0.0,
            )
        ],
        total_claims=1,
        hallucinated_count=0,
        hallucination_rate=0.0,
        passed=True,
    )


def _make_clean_unsupported_report() -> UnsupportedClaimReport:
    return UnsupportedClaimReport(
        claims=[
            UnsupportedClaim(
                claim="Patient has diabetes",
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


def _make_clean_disclaimer_result() -> DisclaimerResult:
    return DisclaimerResult(
        selected_disclaimers=[
            DisclaimerConfig(
                disclaimer_type=DisclaimerType.GENERAL_MEDICAL,
                text="General medical disclaimer",
            )
        ],
    )


@pytest.mark.asyncio
async def test_all_checks_passing():
    validator = DefaultComplianceValidator()
    report = await validator.validate(
        hallucination_report=_make_clean_hallucination_report(),
        unsupported_report=_make_clean_unsupported_report(),
        disclaimer_result=_make_clean_disclaimer_result(),
    )
    assert report.passed is True
    assert report.failed_checks == 0


@pytest.mark.asyncio
async def test_hallucination_check_fails():
    validator = DefaultComplianceValidator()
    hall_report = _make_clean_hallucination_report()
    hall_report.passed = False
    hall_report.hallucination_rate = 0.5
    report = await validator.validate(
        hallucination_report=hall_report,
        unsupported_report=_make_clean_unsupported_report(),
        disclaimer_result=_make_clean_disclaimer_result(),
    )
    hallucination_check = next(
        c for c in report.checks if c.check_name == "Hallucination Check"
    )
    assert hallucination_check.passed is False
    assert report.passed is False


@pytest.mark.asyncio
async def test_unsupported_rate_over_03_fails():
    validator = DefaultComplianceValidator()
    unsup_report = UnsupportedClaimReport(
        claims=[
            UnsupportedClaim(
                claim="Unknown treatment",
                support_level=SupportLevel.UNSUPPORTED,
                confidence=0.9,
            )
        ],
        total_claims=10,
        supported_count=6,
        unsupported_count=4,
        contradictory_count=0,
        coverage_score=0.2,
        passed=False,
    )
    report = await validator.validate(
        hallucination_report=_make_clean_hallucination_report(),
        unsupported_report=unsup_report,
        disclaimer_result=_make_clean_disclaimer_result(),
    )
    unsupported_check = next(
        c for c in report.checks if c.check_name == "Unsupported Claims Check"
    )
    assert unsupported_check.passed is False


@pytest.mark.asyncio
async def test_prohibited_term_guarantee_fails():
    validator = DefaultComplianceValidator()
    hall_report = HallucinationReport(
        results=[
            HallucinationResult(
                claim="This treatment is guaranteed to work",
                hallucination_type=HallucinationType.UNSUPPORTED_CLAIM,
                confidence=0.9,
            )
        ],
        total_claims=1,
        hallucinated_count=0,
        hallucination_rate=0.0,
        passed=True,
    )
    report = await validator.validate(
        hallucination_report=hall_report,
        unsupported_report=_make_clean_unsupported_report(),
        disclaimer_result=_make_clean_disclaimer_result(),
    )
    prohibited_check = next(
        c for c in report.checks if c.check_name == "No Prohibited Claims"
    )
    assert prohibited_check.passed is False
    assert report.passed is False


@pytest.mark.asyncio
async def test_prohibited_term_cure_fails():
    validator = DefaultComplianceValidator()
    hall_report = HallucinationReport(
        results=[
            HallucinationResult(
                claim="This natural remedy will cure your disease",
                hallucination_type=HallucinationType.UNSUPPORTED_CLAIM,
                confidence=0.9,
            )
        ],
        total_claims=1,
        hallucinated_count=0,
        hallucination_rate=0.0,
        passed=True,
    )
    report = await validator.validate(
        hallucination_report=hall_report,
        unsupported_report=_make_clean_unsupported_report(),
        disclaimer_result=_make_clean_disclaimer_result(),
    )
    prohibited_check = next(
        c for c in report.checks if c.check_name == "No Prohibited Claims"
    )
    assert prohibited_check.passed is False


@pytest.mark.asyncio
async def test_absolute_guarantee_definitely_fails():
    validator = DefaultComplianceValidator()
    hall_report = HallucinationReport(
        results=[
            HallucinationResult(
                claim="This will definitely cure your infection",
                hallucination_type=HallucinationType.UNSUPPORTED_CLAIM,
                confidence=0.9,
            )
        ],
        total_claims=1,
        hallucinated_count=0,
        hallucination_rate=0.0,
        passed=True,
    )
    report = await validator.validate(
        hallucination_report=hall_report,
        unsupported_report=_make_clean_unsupported_report(),
        disclaimer_result=_make_clean_disclaimer_result(),
    )
    guarantee_check = next(
        c for c in report.checks if c.check_name == "No Absolute Guarantees"
    )
    assert guarantee_check.passed is False


@pytest.mark.asyncio
async def test_no_disclaimers_fails():
    validator = DefaultComplianceValidator()
    disclaimer_result = DisclaimerResult(selected_disclaimers=[])
    report = await validator.validate(
        hallucination_report=_make_clean_hallucination_report(),
        unsupported_report=_make_clean_unsupported_report(),
        disclaimer_result=disclaimer_result,
    )
    disclaimer_check = next(
        c for c in report.checks if c.check_name == "Disclaimer Present"
    )
    assert disclaimer_check.passed is False
    assert report.passed is False


@pytest.mark.asyncio
async def test_failed_checks_count_correct():
    validator = DefaultComplianceValidator()
    hall_report = HallucinationReport(
        results=[
            HallucinationResult(
                claim="Guaranteed cure for all diseases",
                hallucination_type=HallucinationType.FABRICATED_MEDICATION,
                confidence=0.9,
            ),
            HallucinationResult(
                claim="This is definitely safe",
                hallucination_type=HallucinationType.UNSUPPORTED_CLAIM,
                confidence=0.8,
            ),
        ],
        total_claims=2,
        hallucinated_count=2,
        hallucination_rate=1.0,
        passed=False,
    )
    unsup_report = UnsupportedClaimReport(
        claims=[
            UnsupportedClaim(
                claim="Guaranteed cure for all diseases",
                support_level=SupportLevel.UNSUPPORTED,
                confidence=0.9,
            )
        ],
        total_claims=1,
        supported_count=0,
        unsupported_count=1,
        contradictory_count=0,
        coverage_score=0.0,
        passed=False,
    )
    report = await validator.validate(
        hallucination_report=hall_report,
        unsupported_report=unsup_report,
        disclaimer_result=_make_clean_disclaimer_result(),
    )
    assert report.failed_checks > 0


@pytest.mark.asyncio
async def test_passed_checks_count_correct():
    validator = DefaultComplianceValidator()
    report = await validator.validate(
        hallucination_report=_make_clean_hallucination_report(),
        unsupported_report=_make_clean_unsupported_report(),
        disclaimer_result=_make_clean_disclaimer_result(),
    )
    assert report.passed_checks == report.total_checks
    assert report.passed_checks == 7


@pytest.mark.asyncio
async def test_summary_populated():
    validator = DefaultComplianceValidator()
    report = await validator.validate(
        hallucination_report=_make_clean_hallucination_report(),
        unsupported_report=_make_clean_unsupported_report(),
        disclaimer_result=_make_clean_disclaimer_result(),
    )
    assert report.summary is not None
    assert len(report.summary) > 0


@pytest.mark.asyncio
async def test_multiple_failures():
    validator = DefaultComplianceValidator()
    hall_report = HallucinationReport(
        results=[
            HallucinationResult(
                claim="Guaranteed cure for everything",
                hallucination_type=HallucinationType.FABRICATED_MEDICATION,
                confidence=0.95,
            ),
            HallucinationResult(
                claim="This study definitely proves it",
                hallucination_type=HallucinationType.FABRICATED_CITATION,
                confidence=0.9,
            ),
        ],
        total_claims=2,
        hallucinated_count=2,
        hallucination_rate=1.0,
        passed=False,
    )
    unsup_report = UnsupportedClaimReport(
        claims=[
            UnsupportedClaim(
                claim="Guaranteed cure",
                support_level=SupportLevel.UNSUPPORTED,
                confidence=0.95,
            )
        ],
        total_claims=10,
        supported_count=3,
        unsupported_count=7,
        contradictory_count=0,
        coverage_score=0.1,
        passed=False,
    )
    report = await validator.validate(
        hallucination_report=hall_report,
        unsupported_report=unsup_report,
        disclaimer_result=_make_clean_disclaimer_result(),
    )
    assert report.passed is False
    assert report.failed_checks >= 3


@pytest.mark.asyncio
async def test_evidence_score_below_threshold_fails():
    validator = DefaultComplianceValidator()
    unsup_report = UnsupportedClaimReport(
        claims=[
            UnsupportedClaim(
                claim="Claim with no evidence",
                support_level=SupportLevel.UNSUPPORTED,
                confidence=0.9,
            )
        ],
        total_claims=1,
        supported_count=0,
        unsupported_count=1,
        contradictory_count=0,
        coverage_score=0.0,
        passed=False,
    )
    report = await validator.validate(
        hallucination_report=_make_clean_hallucination_report(),
        unsupported_report=unsup_report,
        disclaimer_result=_make_clean_disclaimer_result(),
    )
    evidence_check = next(
        c for c in report.checks if c.check_name == "Evidence Threshold"
    )
    assert evidence_check.passed is False
