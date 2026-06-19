import pytest

from app.ai.clinical_safety.services.disclaimer import DefaultDisclaimerEngine
from app.ai.clinical_safety.schemas import (
    ClinicalRiskReport,
    ClinicalRiskResult,
    DisclaimerType,
    EmergencyReport,
    EmergencyResult,
    EmergencyType,
    PHIFinding,
    PHIValidationReport,
    PHIType,
    RiskLevel,
)


@pytest.mark.asyncio
async def test_always_adds_general_medical():
    engine = DefaultDisclaimerEngine()
    result = await engine.select(risk_report=None, emergency_report=None)
    types = [d.disclaimer_type for d in result.selected_disclaimers]
    assert DisclaimerType.GENERAL_MEDICAL in types


@pytest.mark.asyncio
async def test_emergency_report_adds_emergency_disclaimer():
    engine = DefaultDisclaimerEngine()
    emergency_report = EmergencyReport(
        has_emergency=True,
        results=[
            EmergencyResult(
                is_emergency=True,
                emergency_type=EmergencyType.CHEST_PAIN,
                indicators=["chest pain"],
            )
        ],
    )
    result = await engine.select(
        risk_report=None, emergency_report=emergency_report
    )
    types = [d.disclaimer_type for d in result.selected_disclaimers]
    assert DisclaimerType.EMERGENCY in types
    assert result.has_emergency_disclaimer is True


@pytest.mark.asyncio
async def test_high_risk_adds_clinical_uncertainty():
    engine = DefaultDisclaimerEngine()
    risk_report = ClinicalRiskReport(
        overall_risk=RiskLevel.HIGH,
        max_risk_score=0.8,
        results=[
            ClinicalRiskResult(
                risk_level=RiskLevel.HIGH, score=0.8
            )
        ],
    )
    result = await engine.select(
        risk_report=risk_report, emergency_report=None
    )
    types = [d.disclaimer_type for d in result.selected_disclaimers]
    assert DisclaimerType.CLINICAL_UNCERTAINTY in types


@pytest.mark.asyncio
async def test_critical_risk_adds_clinical_uncertainty():
    engine = DefaultDisclaimerEngine()
    risk_report = ClinicalRiskReport(
        overall_risk=RiskLevel.CRITICAL,
        max_risk_score=0.95,
        results=[
            ClinicalRiskResult(
                risk_level=RiskLevel.CRITICAL, score=0.95
            )
        ],
    )
    result = await engine.select(
        risk_report=risk_report, emergency_report=None
    )
    types = [d.disclaimer_type for d in result.selected_disclaimers]
    assert DisclaimerType.CLINICAL_UNCERTAINTY in types


@pytest.mark.asyncio
async def test_low_risk_does_not_add_clinical_uncertainty():
    engine = DefaultDisclaimerEngine()
    risk_report = ClinicalRiskReport(
        overall_risk=RiskLevel.LOW,
        max_risk_score=0.1,
        results=[
            ClinicalRiskResult(
                risk_level=RiskLevel.LOW, score=0.1
            )
        ],
    )
    result = await engine.select(
        risk_report=risk_report, emergency_report=None
    )
    types = [d.disclaimer_type for d in result.selected_disclaimers]
    assert DisclaimerType.CLINICAL_UNCERTAINTY not in types


@pytest.mark.asyncio
async def test_get_disclaimers_returns_all_seven_types():
    engine = DefaultDisclaimerEngine()
    disclaimers = await engine.get_disclaimers()
    types = {d.disclaimer_type for d in disclaimers}
    assert len(types) == 7
    for dt in DisclaimerType:
        assert dt in types


@pytest.mark.asyncio
async def test_disclaimer_result_has_correct_flags():
    engine = DefaultDisclaimerEngine()
    emergency_report = EmergencyReport(
        has_emergency=True,
        results=[
            EmergencyResult(
                is_emergency=True,
                emergency_type=EmergencyType.CHEST_PAIN,
                indicators=["chest pain"],
            )
        ],
    )
    result = await engine.select(
        risk_report=None, emergency_report=emergency_report
    )
    assert result.has_emergency_disclaimer is True
    assert isinstance(result.has_medication_disclaimer, bool)
    assert isinstance(result.has_mental_health_disclaimer, bool)


@pytest.mark.asyncio
async def test_selected_disclaimers_populated():
    engine = DefaultDisclaimerEngine()
    result = await engine.select(risk_report=None, emergency_report=None)
    assert len(result.selected_disclaimers) >= 1


@pytest.mark.asyncio
async def test_summary_not_empty():
    engine = DefaultDisclaimerEngine()
    result = await engine.select(risk_report=None, emergency_report=None)
    assert result.summary is not None
    assert len(result.summary) > 0


@pytest.mark.asyncio
async def test_none_reports_handled_gracefully():
    engine = DefaultDisclaimerEngine()
    result = await engine.select(
        risk_report=None, emergency_report=None, phi_report=None
    )
    assert result is not None
    types = [d.disclaimer_type for d in result.selected_disclaimers]
    assert DisclaimerType.GENERAL_MEDICAL in types


@pytest.mark.asyncio
async def test_medication_context_detected():
    engine = DefaultDisclaimerEngine()
    risk_report = ClinicalRiskReport(
        results=[
            ClinicalRiskResult(
                risk_level=RiskLevel.MODERATE,
                score=0.4,
                factors=["The prescribed medication dosage is too high"],
            )
        ],
    )
    result = await engine.select(
        risk_report=risk_report, emergency_report=None
    )
    types = [d.disclaimer_type for d in result.selected_disclaimers]
    assert DisclaimerType.MEDICATION in types
    assert result.has_medication_disclaimer is True


@pytest.mark.asyncio
async def test_mental_health_context_detected():
    engine = DefaultDisclaimerEngine()
    risk_report = ClinicalRiskReport(
        results=[
            ClinicalRiskResult(
                risk_level=RiskLevel.MODERATE,
                score=0.4,
                factors=["Patient shows signs of depression and anxiety"],
            )
        ],
    )
    result = await engine.select(
        risk_report=risk_report, emergency_report=None
    )
    types = [d.disclaimer_type for d in result.selected_disclaimers]
    assert DisclaimerType.MENTAL_HEALTH in types
    assert result.has_mental_health_disclaimer is True


@pytest.mark.asyncio
async def test_pregnancy_context_detected():
    engine = DefaultDisclaimerEngine()
    phi_report = PHIValidationReport(
        findings=[
            PHIFinding(
                phi_type=PHIType.UNKNOWN,
                value_preview="pregnancy",
            )
        ],
    )
    result = await engine.select(
        risk_report=None, emergency_report=None, phi_report=phi_report
    )
    types = [d.disclaimer_type for d in result.selected_disclaimers]
    assert DisclaimerType.PREGNANCY in types


@pytest.mark.asyncio
async def test_pediatric_context_detected():
    engine = DefaultDisclaimerEngine()
    phi_report = PHIValidationReport(
        findings=[
            PHIFinding(
                phi_type=PHIType.UNKNOWN,
                value_preview="child",
            )
        ],
    )
    result = await engine.select(
        risk_report=None, emergency_report=None, phi_report=phi_report
    )
    types = [d.disclaimer_type for d in result.selected_disclaimers]
    assert DisclaimerType.PEDIATRIC in types
