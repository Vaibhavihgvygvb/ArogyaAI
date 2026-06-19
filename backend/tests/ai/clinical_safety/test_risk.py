import pytest

from app.ai.clinical_safety.services.risk import DefaultClinicalRiskEngine
from app.ai.clinical_safety.schemas import (
    ClinicalRiskReport,
    EmergencyReport,
    EmergencyResult,
    EmergencyType,
    HallucinationReport,
    HallucinationResult,
    HallucinationType,
    RiskLevel,
    UnsupportedClaimReport,
    UnsupportedClaim,
    SupportLevel,
)


class TestDefaultClinicalRiskEngine:

    @pytest.mark.asyncio
    async def test_no_reports_returns_low_risk(self):
        engine = DefaultClinicalRiskEngine()
        report = await engine.assess(None, None, None)

        assert report.overall_risk == RiskLevel.LOW
        assert report.max_risk_score == 0.0
        assert report.passed is True
        assert len(report.results) == 1
        assert report.results[0].risk_level == RiskLevel.LOW

    @pytest.mark.asyncio
    async def test_low_hallucination_rate_returns_low_risk(self):
        engine = DefaultClinicalRiskEngine()
        hallu_report = HallucinationReport(
            results=[],
            total_claims=5,
            hallucinated_count=0,
            hallucination_rate=0.0,
            passed=True,
        )
        unsup_report = UnsupportedClaimReport(
            claims=[], total_claims=5, supported_count=5,
            unsupported_count=0, contradictory_count=0,
            coverage_score=1.0, passed=True,
        )
        report = await engine.assess(hallu_report, unsup_report, None)

        assert report.overall_risk == RiskLevel.LOW
        assert report.passed is True

    @pytest.mark.asyncio
    async def test_high_hallucination_rate_increases_risk(self):
        engine = DefaultClinicalRiskEngine()
        hallu_report = HallucinationReport(
            results=[],
            total_claims=10,
            hallucinated_count=8,
            hallucination_rate=0.8,
            passed=False,
        )
        unsup_report = UnsupportedClaimReport(
            claims=[], total_claims=5, supported_count=5,
            unsupported_count=0, contradictory_count=0,
            coverage_score=1.0, passed=True,
        )
        report = await engine.assess(hallu_report, unsup_report, None)

        assert report.overall_risk == RiskLevel.MODERATE
        assert report.max_risk_score > 0.0

    @pytest.mark.asyncio
    async def test_very_high_hallucination_rate_can_reach_high_risk(self):
        engine = DefaultClinicalRiskEngine()
        hallu_report = HallucinationReport(
            results=[],
            total_claims=10,
            hallucinated_count=10,
            hallucination_rate=1.0,
            passed=False,
        )
        unsup_report = UnsupportedClaimReport(
            claims=[], total_claims=5, supported_count=0,
            unsupported_count=5, contradictory_count=0,
            coverage_score=0.0, passed=False,
        )
        report = await engine.assess(hallu_report, unsup_report, None)

        assert report.overall_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        assert report.max_risk_score >= 0.5

    @pytest.mark.asyncio
    async def test_high_unsupported_rate_increases_risk(self):
        engine = DefaultClinicalRiskEngine()
        hallu_report = HallucinationReport(
            results=[],
            total_claims=10,
            hallucinated_count=10,
            hallucination_rate=1.0,
            passed=False,
        )
        low_unsup = UnsupportedClaimReport(
            claims=[], total_claims=5, supported_count=5,
            unsupported_count=0, contradictory_count=0,
            coverage_score=1.0, passed=True,
        )
        high_unsup = UnsupportedClaimReport(
            claims=[], total_claims=5, supported_count=0,
            unsupported_count=5, contradictory_count=0,
            coverage_score=0.0, passed=False,
        )
        low_report = await engine.assess(hallu_report, low_unsup, None)
        high_report = await engine.assess(hallu_report, high_unsup, None)

        assert low_report.max_risk_score < high_report.max_risk_score

    @pytest.mark.asyncio
    async def test_emergency_indicators_increase_risk(self):
        engine = DefaultClinicalRiskEngine()
        base_report = await engine.assess(None, None, None)

        emergency = EmergencyReport(
            results=[
                EmergencyResult(
                    is_emergency=True,
                    emergency_type=EmergencyType.CHEST_PAIN,
                    confidence=0.95,
                    indicators=["chest pain", "chest tightness"],
                    severity="high",
                    disclaimer_required=True,
                )
            ],
            has_emergency=True,
            max_severity="high",
            requires_override=True,
        )
        emg_report = await engine.assess(None, None, emergency)

        assert base_report.max_risk_score < emg_report.max_risk_score

    @pytest.mark.asyncio
    async def test_topic_sensitivity_increases_risk(self):
        engine = DefaultClinicalRiskEngine()
        no_topic = await engine.assess(None, None, None)

        hallu_report = HallucinationReport(
            results=[
                HallucinationResult(
                    claim="The patient has cancer and heart disease.",
                    hallucination_type=HallucinationType.UNSUPPORTED_CLAIM,
                    confidence=0.4,
                )
            ],
            total_claims=1,
            hallucinated_count=1,
            hallucination_rate=1.0,
            passed=False,
        )
        topic_report = await engine.assess(hallu_report, None, None)

        assert topic_report.max_risk_score > no_topic.max_risk_score

    @pytest.mark.asyncio
    async def test_critical_risk_with_very_high_scores(self):
        engine = DefaultClinicalRiskEngine()
        hallu_report = HallucinationReport(
            results=[],
            total_claims=10,
            hallucinated_count=10,
            hallucination_rate=1.0,
            passed=False,
        )
        unsup_report = UnsupportedClaimReport(
            claims=[], total_claims=5, supported_count=0,
            unsupported_count=5, contradictory_count=0,
            coverage_score=0.0, passed=False,
        )
        emergency = EmergencyReport(
            results=[
                EmergencyResult(
                    is_emergency=True,
                    emergency_type=EmergencyType.SUICIDAL_IDEATION,
                    confidence=0.95,
                    indicators=["suicide", "suicidal", "overdose", "self-harm"],
                    severity="critical",
                    disclaimer_required=True,
                )
            ],
            has_emergency=True,
            max_severity="critical",
            requires_override=True,
        )
        report = await engine.assess(hallu_report, unsup_report, emergency)

        assert report.overall_risk == RiskLevel.CRITICAL
        assert report.passed is False

    @pytest.mark.asyncio
    async def test_moderate_risk_with_mid_range_scores(self):
        engine = DefaultClinicalRiskEngine()
        hallu_report = HallucinationReport(
            results=[],
            total_claims=10,
            hallucinated_count=8,
            hallucination_rate=0.8,
            passed=False,
        )
        report = await engine.assess(hallu_report, None, None)

        assert report.overall_risk == RiskLevel.MODERATE
        assert 0.25 <= report.max_risk_score < 0.5

    @pytest.mark.asyncio
    async def test_risk_report_has_correct_overall_risk_enum(self):
        engine = DefaultClinicalRiskEngine()
        report = await engine.assess(None, None, None)

        assert isinstance(report, ClinicalRiskReport)
        assert isinstance(report.overall_risk, RiskLevel)
        assert report.overall_risk == RiskLevel.LOW

    @pytest.mark.asyncio
    async def test_max_risk_score_correctly_computed(self):
        engine = DefaultClinicalRiskEngine()
        hallu_report = HallucinationReport(
            results=[],
            total_claims=10,
            hallucinated_count=5,
            hallucination_rate=0.5,
            passed=False,
        )
        report = await engine.assess(hallu_report, None, None)

        expected_hallu_impact = min(1.0, 0.5 * 1.5)
        expected_score = expected_hallu_impact * 0.30
        assert report.max_risk_score == pytest.approx(expected_score, rel=1e-5)

    @pytest.mark.asyncio
    async def test_factors_list_populated(self):
        engine = DefaultClinicalRiskEngine()
        hallu_report = HallucinationReport(
            results=[
                HallucinationResult(
                    claim="Patient has cancer.",
                    hallucination_type=HallucinationType.FABRICATED_DISEASE,
                    confidence=0.75,
                )
            ],
            total_claims=1,
            hallucinated_count=1,
            hallucination_rate=1.0,
            passed=False,
        )
        unsup_report = UnsupportedClaimReport(
            claims=[], total_claims=5, supported_count=0,
            unsupported_count=5, contradictory_count=0,
            coverage_score=0.0, passed=False,
        )
        report = await engine.assess(hallu_report, unsup_report, None)

        assert len(report.results[0].factors) > 0
        factor_text = " ".join(report.results[0].factors).lower()
        assert "hallucination" in factor_text
        assert "unsupported" in factor_text

    @pytest.mark.asyncio
    async def test_emergency_indicators_propagate(self):
        engine = DefaultClinicalRiskEngine()
        emergency = EmergencyReport(
            results=[
                EmergencyResult(
                    is_emergency=True,
                    emergency_type=EmergencyType.CHEST_PAIN,
                    confidence=0.95,
                    indicators=["chest pain"],
                    severity="high",
                    disclaimer_required=True,
                )
            ],
            has_emergency=True,
            max_severity="high",
            requires_override=True,
        )
        report = await engine.assess(None, None, emergency)

        assert len(report.results[0].emergency_indicators) > 0
        assert "chest pain" in report.results[0].emergency_indicators

    @pytest.mark.asyncio
    async def test_none_hallucination_report_handling(self):
        engine = DefaultClinicalRiskEngine()
        report = await engine.assess(None, None, None)

        assert report.overall_risk == RiskLevel.LOW
        assert report.max_risk_score == 0.0
        assert report.passed is True
