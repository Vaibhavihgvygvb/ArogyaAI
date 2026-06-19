from pydantic import ValidationError
import pytest

from app.ai.clinical_safety.schemas import (
    HallucinationType,
    SupportLevel,
    RiskLevel,
    EmergencyType,
    PHIType,
    DisclaimerType,
    ApprovalDecision,
    HallucinationResult,
    HallucinationReport,
    UnsupportedClaim,
    UnsupportedClaimReport,
    ClinicalRiskResult,
    ClinicalRiskReport,
    EmergencyResult,
    EmergencyReport,
    PHIFinding,
    PHIValidationReport,
    DisclaimerConfig,
    DisclaimerResult,
    ComplianceCheck,
    ComplianceReport,
    ApprovalResult,
    SafetyState,
    PipelineResult,
    SafetyServiceResult,
)


class TestHallucinationTypeEnum:
    def test_values(self):
        assert HallucinationType.FABRICATED_MEDICATION.value == "fabricated_medication"
        assert HallucinationType.FABRICATED_DISEASE.value == "fabricated_disease"
        assert HallucinationType.FABRICATED_CITATION.value == "fabricated_citation"
        assert HallucinationType.FABRICATED_GUIDELINE.value == "fabricated_guideline"
        assert HallucinationType.FABRICATED_STATISTIC.value == "fabricated_statistic"
        assert HallucinationType.FABRICATED_RECOMMENDATION.value == "fabricated_recommendation"
        assert HallucinationType.UNSUPPORTED_CLAIM.value == "unsupported_claim"
        assert HallucinationType.CONTRADICTED_CLAIM.value == "contradicted_claim"
        assert HallucinationType.UNKNOWN.value == "unknown"

    def test_members(self):
        assert len(HallucinationType) == 9


class TestSupportLevelEnum:
    def test_values(self):
        assert SupportLevel.FULLY_SUPPORTED.value == "fully_supported"
        assert SupportLevel.PARTIALLY_SUPPORTED.value == "partially_supported"
        assert SupportLevel.UNSUPPORTED.value == "unsupported"
        assert SupportLevel.CONTRADICTORY.value == "contradictory"

    def test_members(self):
        assert len(SupportLevel) == 4


class TestRiskLevelEnum:
    def test_values(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MODERATE.value == "moderate"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_members(self):
        assert len(RiskLevel) == 4


class TestEmergencyTypeEnum:
    def test_values(self):
        assert EmergencyType.CHEST_PAIN.value == "chest_pain"
        assert EmergencyType.STROKE_SYMPTOMS.value == "stroke_symptoms"
        assert EmergencyType.SEVERE_BLEEDING.value == "severe_bleeding"
        assert EmergencyType.SUICIDAL_IDEATION.value == "suicidal_ideation"
        assert EmergencyType.ANAPHYLAXIS.value == "anaphylaxis"
        assert EmergencyType.RESPIRATORY_DISTRESS.value == "respiratory_distress"
        assert EmergencyType.LOSS_OF_CONSCIOUSNESS.value == "loss_of_consciousness"
        assert EmergencyType.SEVERE_ALLERGIC_REACTION.value == "severe_allergic_reaction"
        assert EmergencyType.OVERDOSE.value == "overdose"
        assert EmergencyType.UNKNOWN.value == "unknown"

    def test_members(self):
        assert len(EmergencyType) == 10


class TestPHITypeEnum:
    def test_values(self):
        assert PHIType.SSN.value == "ssn"
        assert PHIType.EMAIL.value == "email"
        assert PHIType.PHONE.value == "phone"
        assert PHIType.AADHAAR.value == "aadhaar"
        assert PHIType.PASSPORT.value == "passport"
        assert PHIType.CREDIT_CARD.value == "credit_card"
        assert PHIType.MEDICAL_RECORD_NUMBER.value == "medical_record_number"
        assert PHIType.PATIENT_NAME.value == "patient_name"
        assert PHIType.ADDRESS.value == "address"
        assert PHIType.INSURANCE_ID.value == "insurance_id"
        assert PHIType.DOB.value == "dob"
        assert PHIType.UNKNOWN.value == "unknown"

    def test_members(self):
        assert len(PHIType) == 12


class TestDisclaimerTypeEnum:
    def test_values(self):
        assert DisclaimerType.GENERAL_MEDICAL.value == "general_medical"
        assert DisclaimerType.EMERGENCY.value == "emergency"
        assert DisclaimerType.MEDICATION.value == "medication"
        assert DisclaimerType.MENTAL_HEALTH.value == "mental_health"
        assert DisclaimerType.PREGNANCY.value == "pregnancy"
        assert DisclaimerType.PEDIATRIC.value == "pediatric"
        assert DisclaimerType.CLINICAL_UNCERTAINTY.value == "clinical_uncertainty"

    def test_members(self):
        assert len(DisclaimerType) == 7


class TestApprovalDecisionEnum:
    def test_values(self):
        assert ApprovalDecision.APPROVED.value == "approved"
        assert ApprovalDecision.APPROVED_WITH_WARNINGS.value == "approved_with_warnings"
        assert ApprovalDecision.ESCALATE.value == "escalate"
        assert ApprovalDecision.REJECT.value == "reject"

    def test_members(self):
        assert len(ApprovalDecision) == 4


class TestHallucinationResult:
    def test_required_fields(self):
        hr = HallucinationResult(
            claim="patient has diabetes",
            hallucination_type=HallucinationType.FABRICATED_MEDICATION,
            confidence=0.95,
        )
        assert hr.claim == "patient has diabetes"
        assert hr.hallucination_type == HallucinationType.FABRICATED_MEDICATION
        assert hr.confidence == 0.95

    def test_defaults(self):
        hr = HallucinationResult(
            claim="test claim",
            hallucination_type=HallucinationType.UNKNOWN,
            confidence=0.5,
        )
        assert hr.evidence_snippet is None
        assert hr.details is None
        assert hr.span_start == 0
        assert hr.span_end == 0

    def test_with_all_fields(self):
        hr = HallucinationResult(
            claim="patient has diabetes",
            hallucination_type=HallucinationType.FABRICATED_STATISTIC,
            confidence=0.85,
            evidence_snippet="no evidence found",
            details="statistic does not match any known source",
            span_start=10,
            span_end=30,
        )
        assert hr.evidence_snippet == "no evidence found"
        assert hr.details == "statistic does not match any known source"
        assert hr.span_start == 10
        assert hr.span_end == 30

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            HallucinationResult(
                claim="c", hallucination_type=HallucinationType.UNKNOWN, confidence=1.5
            )
        with pytest.raises(ValidationError):
            HallucinationResult(
                claim="c", hallucination_type=HallucinationType.UNKNOWN, confidence=-0.1
            )


class TestHallucinationReport:
    def test_defaults(self):
        report = HallucinationReport()
        assert report.results == []
        assert report.total_claims == 0
        assert report.hallucinated_count == 0
        assert report.hallucination_rate == 0.0
        assert report.passed is True
        assert report.summary is None

    def test_hallucination_rate_calculation(self):
        results = [
            HallucinationResult(claim="c1", hallucination_type=HallucinationType.UNKNOWN, confidence=0.5),
            HallucinationResult(claim="c2", hallucination_type=HallucinationType.FABRICATED_MEDICATION, confidence=0.9),
        ]
        report = HallucinationReport(
            results=results,
            total_claims=2,
            hallucinated_count=1,
            hallucination_rate=0.5,
        )
        assert report.hallucination_rate == 0.5
        assert report.total_claims == 2
        assert report.hallucinated_count == 1
        assert len(report.results) == 2

    def test_passed_flag_false_when_high_hallucination(self):
        report = HallucinationReport(passed=False, summary="high hallucination rate")
        assert report.passed is False
        assert report.summary == "high hallucination rate"

    def test_te_back_to_orm(self):
        report = HallucinationReport()
        assert hasattr(report, "model_config")
        assert report.model_config.get("from_attributes") is True


class TestUnsupportedClaim:
    def test_required_fields(self):
        uc = UnsupportedClaim(
            claim="this drug cures everything",
            support_level=SupportLevel.UNSUPPORTED,
            confidence=0.95,
        )
        assert uc.claim == "this drug cures everything"
        assert uc.support_level == SupportLevel.UNSUPPORTED
        assert uc.confidence == 0.95

    def test_all_support_levels(self):
        for level in SupportLevel:
            uc = UnsupportedClaim(
                claim="test", support_level=level, confidence=0.5
            )
            assert uc.support_level == level

    def test_defaults(self):
        uc = UnsupportedClaim(
            claim="test", support_level=SupportLevel.PARTIALLY_SUPPORTED, confidence=0.6
        )
        assert uc.matched_evidence == []
        assert uc.missing_evidence == []
        assert uc.details is None

    def test_with_evidence(self):
        uc = UnsupportedClaim(
            claim="test",
            support_level=SupportLevel.CONTRADICTORY,
            confidence=0.8,
            matched_evidence=["study A"],
            missing_evidence=["study B"],
            details="contradictory evidence found",
        )
        assert uc.matched_evidence == ["study A"]
        assert uc.missing_evidence == ["study B"]
        assert uc.details == "contradictory evidence found"

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            UnsupportedClaim(
                claim="c", support_level=SupportLevel.UNSUPPORTED, confidence=1.2
            )


class TestUnsupportedClaimReport:
    def test_defaults(self):
        report = UnsupportedClaimReport()
        assert report.claims == []
        assert report.total_claims == 0
        assert report.supported_count == 0
        assert report.unsupported_count == 0
        assert report.contradictory_count == 0
        assert report.coverage_score == 0.0
        assert report.passed is True
        assert report.summary is None

    def test_coverage_calculation(self):
        claims = [
            UnsupportedClaim(claim="c1", support_level=SupportLevel.FULLY_SUPPORTED, confidence=0.9),
            UnsupportedClaim(claim="c2", support_level=SupportLevel.UNSUPPORTED, confidence=0.8),
            UnsupportedClaim(claim="c3", support_level=SupportLevel.PARTIALLY_SUPPORTED, confidence=0.6),
            UnsupportedClaim(claim="c4", support_level=SupportLevel.CONTRADICTORY, confidence=0.7),
        ]
        report = UnsupportedClaimReport(
            claims=claims,
            total_claims=4,
            supported_count=1,
            unsupported_count=2,
            contradictory_count=1,
            coverage_score=0.75,
        )
        assert report.coverage_score == 0.75
        assert report.total_claims == 4
        assert report.supported_count == 1
        assert report.unsupported_count == 2
        assert report.contradictory_count == 1
        assert len(report.claims) == 4


class TestClinicalRiskResult:
    def test_required_fields(self):
        cr = ClinicalRiskResult(risk_level=RiskLevel.HIGH, score=0.85)
        assert cr.risk_level == RiskLevel.HIGH
        assert cr.score == 0.85

    def test_defaults(self):
        cr = ClinicalRiskResult(risk_level=RiskLevel.LOW, score=0.1)
        assert cr.factors == []
        assert cr.confidence_impact == 0.0
        assert cr.unsupported_impact == 0.0
        assert cr.topic_sensitivity == 0.0
        assert cr.emergency_indicators == []
        assert cr.details is None

    def test_with_all_fields(self):
        cr = ClinicalRiskResult(
            risk_level=RiskLevel.CRITICAL,
            score=0.95,
            factors=["high toxicity", "drug interaction"],
            confidence_impact=0.4,
            unsupported_impact=0.3,
            topic_sensitivity=0.9,
            emergency_indicators=["overdose risk"],
            details="critical risk detected",
        )
        assert cr.factors == ["high toxicity", "drug interaction"]
        assert cr.confidence_impact == 0.4
        assert cr.topic_sensitivity == 0.9
        assert cr.details == "critical risk detected"

    def test_all_risk_levels(self):
        for level in RiskLevel:
            cr = ClinicalRiskResult(risk_level=level, score=0.5)
            assert cr.risk_level == level

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            ClinicalRiskResult(risk_level=RiskLevel.LOW, score=1.5)


class TestClinicalRiskReport:
    def test_defaults(self):
        report = ClinicalRiskReport()
        assert report.results == []
        assert report.overall_risk == RiskLevel.LOW
        assert report.max_risk_score == 0.0
        assert report.passed is True
        assert report.summary is None

    def test_with_results(self):
        results = [
            ClinicalRiskResult(risk_level=RiskLevel.HIGH, score=0.85),
            ClinicalRiskResult(risk_level=RiskLevel.MODERATE, score=0.55),
        ]
        report = ClinicalRiskReport(
            results=results,
            overall_risk=RiskLevel.HIGH,
            max_risk_score=0.85,
            passed=False,
            summary="high risk detected",
        )
        assert len(report.results) == 2
        assert report.overall_risk == RiskLevel.HIGH
        assert report.max_risk_score == 0.85
        assert report.passed is False
        assert report.summary == "high risk detected"


class TestEmergencyResult:
    def test_is_emergency_true(self):
        er = EmergencyResult(
            is_emergency=True,
            emergency_type=EmergencyType.CHEST_PAIN,
            confidence=0.95,
        )
        assert er.is_emergency is True
        assert er.emergency_type == EmergencyType.CHEST_PAIN
        assert er.confidence == 0.95

    def test_is_emergency_false(self):
        er = EmergencyResult(is_emergency=False)
        assert er.is_emergency is False
        assert er.emergency_type is None
        assert er.confidence == 0.0

    def test_defaults(self):
        er = EmergencyResult(is_emergency=False)
        assert er.indicators == []
        assert er.severity == "medium"
        assert er.recommended_action is None
        assert er.disclaimer_required is True
        assert er.details is None

    def test_with_all_fields(self):
        er = EmergencyResult(
            is_emergency=True,
            emergency_type=EmergencyType.STROKE_SYMPTOMS,
            confidence=0.98,
            indicators=["facial drooping", "slurred speech"],
            severity="high",
            recommended_action="call 911 immediately",
            disclaimer_required=True,
            details="FAST criteria positive",
        )
        assert er.indicators == ["facial drooping", "slurred speech"]
        assert er.severity == "high"
        assert er.recommended_action == "call 911 immediately"
        assert er.details == "FAST criteria positive"


class TestEmergencyReport:
    def test_defaults(self):
        report = EmergencyReport()
        assert report.results == []
        assert report.has_emergency is False
        assert report.max_severity == "none"
        assert report.requires_override is False
        assert report.summary is None

    def test_with_emergency(self):
        results = [
            EmergencyResult(
                is_emergency=True,
                emergency_type=EmergencyType.CHEST_PAIN,
                severity="high",
            )
        ]
        report = EmergencyReport(
            results=results,
            has_emergency=True,
            max_severity="high",
            requires_override=True,
            summary="emergency detected",
        )
        assert report.has_emergency is True
        assert report.max_severity == "high"
        assert report.requires_override is True
        assert report.summary == "emergency detected"
        assert len(report.results) == 1


class TestPHIFinding:
    def test_required_fields(self):
        finding = PHIFinding(phi_type=PHIType.SSN, value_preview="***-**-1234")
        assert finding.phi_type == PHIType.SSN
        assert finding.value_preview == "***-**-1234"

    def test_defaults(self):
        finding = PHIFinding(phi_type=PHIType.EMAIL, value_preview="u***@e.com")
        assert finding.location is None
        assert finding.confidence == 0.0
        assert finding.risk == "medium"

    def test_with_all_fields(self):
        finding = PHIFinding(
            phi_type=PHIType.PHONE,
            value_preview="***-***-5678",
            location="patient_note.txt:42",
            confidence=0.95,
            risk="high",
        )
        assert finding.location == "patient_note.txt:42"
        assert finding.confidence == 0.95
        assert finding.risk == "high"

    def test_all_phi_types(self):
        for phi_type in PHIType:
            finding = PHIFinding(phi_type=phi_type, value_preview="preview")
            assert finding.phi_type == phi_type


class TestPHIValidationReport:
    def test_defaults(self):
        report = PHIValidationReport()
        assert report.findings == []
        assert report.total_findings == 0
        assert report.has_phi is False
        assert report.passed is True
        assert report.summary is None

    def test_with_findings(self):
        findings = [
            PHIFinding(phi_type=PHIType.SSN, value_preview="***-***-0000"),
            PHIFinding(phi_type=PHIType.EMAIL, value_preview="u***@e.com"),
        ]
        report = PHIValidationReport(
            findings=findings,
            total_findings=2,
            has_phi=True,
            passed=False,
            summary="PHI detected",
        )
        assert report.has_phi is True
        assert report.passed is False
        assert report.total_findings == 2
        assert len(report.findings) == 2

    def test_passed_logic(self):
        report = PHIValidationReport(passed=False)
        assert report.passed is False
        report_no_phi = PHIValidationReport(has_phi=False, passed=True)
        assert report_no_phi.passed is True


class TestDisclaimerConfig:
    def test_required_fields(self):
        dc = DisclaimerConfig(
            disclaimer_type=DisclaimerType.GENERAL_MEDICAL,
            text="this is not medical advice",
        )
        assert dc.disclaimer_type == DisclaimerType.GENERAL_MEDICAL
        assert dc.text == "this is not medical advice"

    def test_defaults(self):
        dc = DisclaimerConfig(
            disclaimer_type=DisclaimerType.MEDICATION,
            text="consult your doctor",
        )
        assert dc.severity == "informational"
        assert dc.required is True
        assert dc.use_emergency_override is False

    def test_with_all_fields(self):
        dc = DisclaimerConfig(
            disclaimer_type=DisclaimerType.EMERGENCY,
            text="call 911",
            severity="high",
            required=True,
            use_emergency_override=True,
        )
        assert dc.severity == "high"
        assert dc.use_emergency_override is True

    def test_all_disclaimer_types(self):
        for dt in DisclaimerType:
            dc = DisclaimerConfig(disclaimer_type=dt, text="disclaimer text")
            assert dc.disclaimer_type == dt


class TestDisclaimerResult:
    def test_defaults(self):
        dr = DisclaimerResult()
        assert dr.selected_disclaimers == []
        assert dr.has_emergency_disclaimer is False
        assert dr.has_medication_disclaimer is False
        assert dr.has_mental_health_disclaimer is False
        assert dr.summary is None

    def test_with_disclaimers(self):
        disclaimers = [
            DisclaimerConfig(
                disclaimer_type=DisclaimerType.EMERGENCY,
                text="call 911",
            ),
            DisclaimerConfig(
                disclaimer_type=DisclaimerType.MEDICATION,
                text="consult doctor",
            ),
            DisclaimerConfig(
                disclaimer_type=DisclaimerType.MENTAL_HEALTH,
                text="seek help",
            ),
        ]
        dr = DisclaimerResult(
            selected_disclaimers=disclaimers,
            has_emergency_disclaimer=True,
            has_medication_disclaimer=True,
            has_mental_health_disclaimer=True,
            summary="3 disclaimers applied",
        )
        assert len(dr.selected_disclaimers) == 3
        assert dr.has_emergency_disclaimer is True
        assert dr.has_medication_disclaimer is True
        assert dr.has_mental_health_disclaimer is True
        assert dr.summary == "3 disclaimers applied"

    def test_flags_independent(self):
        dr = DisclaimerResult(
            selected_disclaimers=[],
            has_emergency_disclaimer=False,
            has_medication_disclaimer=True,
            has_mental_health_disclaimer=False,
        )
        assert dr.has_emergency_disclaimer is False
        assert dr.has_medication_disclaimer is True
        assert dr.has_mental_health_disclaimer is False


class TestComplianceCheck:
    def test_required_fields(self):
        cc = ComplianceCheck(check_name="hipaa", passed=True)
        assert cc.check_name == "hipaa"
        assert cc.passed is True

    def test_defaults(self):
        cc = ComplianceCheck(check_name="gdpr", passed=False)
        assert cc.severity == "medium"
        assert cc.details is None

    def test_with_details(self):
        cc = ComplianceCheck(
            check_name="hipaa", passed=False, severity="high", details="missing patient consent"
        )
        assert cc.severity == "high"
        assert cc.details == "missing patient consent"


class TestComplianceReport:
    def test_defaults(self):
        report = ComplianceReport()
        assert report.checks == []
        assert report.total_checks == 0
        assert report.passed_checks == 0
        assert report.failed_checks == 0
        assert report.passed is True
        assert report.summary is None

    def test_counts(self):
        checks = [
            ComplianceCheck(check_name="c1", passed=True),
            ComplianceCheck(check_name="c2", passed=False),
            ComplianceCheck(check_name="c3", passed=True),
        ]
        report = ComplianceReport(
            checks=checks,
            total_checks=3,
            passed_checks=2,
            failed_checks=1,
            passed=False,
            summary="1 check failed",
        )
        assert report.total_checks == 3
        assert report.passed_checks == 2
        assert report.failed_checks == 1
        assert report.passed is False
        assert report.summary == "1 check failed"
        assert len(report.checks) == 3


class TestApprovalResult:
    def test_approved(self):
        ar = ApprovalResult(decision=ApprovalDecision.APPROVED)
        assert ar.decision == ApprovalDecision.APPROVED

    def test_approved_with_warnings(self):
        ar = ApprovalResult(
            decision=ApprovalDecision.APPROVED_WITH_WARNINGS,
            warnings=["low confidence on some claims"],
        )
        assert ar.decision == ApprovalDecision.APPROVED_WITH_WARNINGS
        assert ar.warnings == ["low confidence on some claims"]

    def test_escalate(self):
        ar = ApprovalResult(
            decision=ApprovalDecision.ESCALATE,
            requires_escalation=True,
        )
        assert ar.decision == ApprovalDecision.ESCALATE
        assert ar.requires_escalation is True

    def test_reject(self):
        ar = ApprovalResult(
            decision=ApprovalDecision.REJECT,
            reasons=["hallucination detected", "unsupported claims"],
            requires_override=True,
        )
        assert ar.decision == ApprovalDecision.REJECT
        assert ar.reasons == ["hallucination detected", "unsupported claims"]
        assert ar.requires_override is True

    def test_defaults(self):
        ar = ApprovalResult(decision=ApprovalDecision.APPROVED)
        assert ar.reasons == []
        assert ar.warnings == []
        assert ar.requires_escalation is False
        assert ar.requires_override is False
        assert ar.summary is None

    def test_all_decisions(self):
        for decision in ApprovalDecision:
            ar = ApprovalResult(decision=decision)
            assert ar.decision == decision


class TestSafetyState:
    def test_defaults(self):
        state = SafetyState()
        assert state.response_text == ""
        assert state.claims == []
        assert state.evidence_report is None
        assert state.hallucination_report is None
        assert state.unsupported_report is None
        assert state.risk_report is None
        assert state.emergency_report is None
        assert state.phi_report is None
        assert state.disclaimer_result is None
        assert state.compliance_report is None
        assert state.approval_result is None
        assert state.config == {}

    def test_with_nested_hallucination_report(self):
        hr = HallucinationResult(
            claim="test", hallucination_type=HallucinationType.UNKNOWN, confidence=0.5
        )
        report = HallucinationReport(
            results=[hr], total_claims=1, hallucinated_count=0, hallucination_rate=0.0
        )
        state = SafetyState(hallucination_report=report)
        assert state.hallucination_report is not None
        assert len(state.hallucination_report.results) == 1
        assert state.hallucination_report.hallucination_rate == 0.0

    def test_with_nested_unsupported_report(self):
        uc = UnsupportedClaim(
            claim="test", support_level=SupportLevel.FULLY_SUPPORTED, confidence=0.9
        )
        report = UnsupportedClaimReport(
            claims=[uc], total_claims=1, supported_count=1, coverage_score=1.0
        )
        state = SafetyState(unsupported_report=report)
        assert state.unsupported_report is not None
        assert state.unsupported_report.coverage_score == 1.0

    def test_with_nested_risk_report(self):
        rr = ClinicalRiskReport(
            overall_risk=RiskLevel.HIGH, max_risk_score=0.85, passed=False
        )
        state = SafetyState(risk_report=rr)
        assert state.risk_report is not None
        assert state.risk_report.overall_risk == RiskLevel.HIGH

    def test_with_nested_emergency_report(self):
        er = EmergencyReport(has_emergency=True, max_severity="high")
        state = SafetyState(emergency_report=er)
        assert state.emergency_report is not None
        assert state.emergency_report.has_emergency is True

    def test_with_nested_phi_report(self):
        pr = PHIValidationReport(has_phi=True, passed=False)
        state = SafetyState(phi_report=pr)
        assert state.phi_report is not None
        assert state.phi_report.has_phi is True

    def test_with_nested_disclaimer_result(self):
        dr = DisclaimerResult(
            has_emergency_disclaimer=True, summary="emergency disclaimer"
        )
        state = SafetyState(disclaimer_result=dr)
        assert state.disclaimer_result is not None
        assert state.disclaimer_result.has_emergency_disclaimer is True

    def test_with_nested_compliance_report(self):
        cr = ComplianceReport(total_checks=1, passed_checks=1)
        state = SafetyState(compliance_report=cr)
        assert state.compliance_report is not None
        assert state.compliance_report.passed_checks == 1

    def test_with_nested_approval_result(self):
        ar = ApprovalResult(decision=ApprovalDecision.APPROVED)
        state = SafetyState(approval_result=ar)
        assert state.approval_result is not None
        assert state.approval_result.decision == ApprovalDecision.APPROVED

    def test_with_config(self):
        state = SafetyState(config={"threshold": 0.5, "enabled": True})
        assert state.config == {"threshold": 0.5, "enabled": True}

    def test_with_response_text_and_claims(self):
        state = SafetyState(
            response_text="patient has diabetes",
            claims=["patient has diabetes"],
        )
        assert state.response_text == "patient has diabetes"
        assert state.claims == ["patient has diabetes"]


class TestPipelineResult:
    def test_minimal(self):
        state = SafetyState()
        pr = PipelineResult(state=state)
        assert pr.state == state
        assert pr.pipeline_name == "clinical_safety"
        assert pr.total_processing_time_ms == 0.0
        assert pr.steps_completed == []
        assert pr.steps_skipped == []
        assert pr.errors == []
        assert pr.success is True

    def test_with_steps_and_errors(self):
        state = SafetyState()
        pr = PipelineResult(
            state=state,
            pipeline_name="clinical_safety_v2",
            total_processing_time_ms=350.0,
            steps_completed=["detect_hallucinations", "check_claims", "assess_risk"],
            steps_skipped=["phi_scan"],
            errors=["emergency detection timeout"],
            success=False,
        )
        assert pr.pipeline_name == "clinical_safety_v2"
        assert pr.total_processing_time_ms == 350.0
        assert pr.steps_completed == ["detect_hallucinations", "check_claims", "assess_risk"]
        assert pr.steps_skipped == ["phi_scan"]
        assert pr.errors == ["emergency detection timeout"]
        assert pr.success is False


class TestSafetyServiceResult:
    def test_defaults(self):
        sr = SafetyServiceResult()
        assert sr.passed is False
        assert sr.pipeline_result is None
        assert sr.approval is None
        assert sr.summary is None
        assert sr.warnings == []
        assert sr.errors == []
        assert sr.processing_time_ms == 0.0

    def test_with_passed_summary(self):
        state = SafetyState()
        pr = PipelineResult(state=state, success=True)
        ar = ApprovalResult(decision=ApprovalDecision.APPROVED)
        sr = SafetyServiceResult(
            passed=True,
            pipeline_result=pr,
            approval=ar,
            summary="all safety checks passed",
            warnings=["low confidence on one claim"],
            errors=[],
            processing_time_ms=250.0,
        )
        assert sr.passed is True
        assert sr.pipeline_result == pr
        assert sr.approval == ar
        assert sr.summary == "all safety checks passed"
        assert sr.warnings == ["low confidence on one claim"]
        assert sr.processing_time_ms == 250.0

    def test_with_errors(self):
        sr = SafetyServiceResult(
            passed=False,
            errors=["hallucination detected"],
            summary="safety check failed",
        )
        assert sr.passed is False
        assert sr.errors == ["hallucination detected"]
        assert sr.summary == "safety check failed"


class TestDefaultFactories:
    def test_hallucination_result_evidence_snippet_default(self):
        hr = HallucinationResult(
            claim="c", hallucination_type=HallucinationType.UNKNOWN, confidence=0.5
        )
        assert hr.evidence_snippet is None
        assert hr.span_start == 0

    def test_hallucination_report_results_factory(self):
        report = HallucinationReport()
        assert report.results == []
        report.results.append(
            HallucinationResult(
                claim="c", hallucination_type=HallucinationType.UNKNOWN, confidence=0.5
            )
        )
        assert len(report.results) == 1

    def test_unsupported_claim_evidence_factory(self):
        uc = UnsupportedClaim(
            claim="c", support_level=SupportLevel.UNSUPPORTED, confidence=0.8
        )
        assert uc.matched_evidence == []
        assert uc.missing_evidence == []

    def test_unsupported_claim_report_claims_factory(self):
        report = UnsupportedClaimReport()
        assert report.claims == []

    def test_clinical_risk_result_factors_factory(self):
        cr = ClinicalRiskResult(risk_level=RiskLevel.LOW, score=0.1)
        assert cr.factors == []
        assert cr.emergency_indicators == []

    def test_clinical_risk_report_results_factory(self):
        report = ClinicalRiskReport()
        assert report.results == []

    def test_emergency_result_indicators_factory(self):
        er = EmergencyResult(is_emergency=False)
        assert er.indicators == []

    def test_emergency_report_results_factory(self):
        report = EmergencyReport()
        assert report.results == []

    def test_phi_finding_defaults(self):
        finding = PHIFinding(phi_type=PHIType.SSN, value_preview="preview")
        assert finding.confidence == 0.0
        assert finding.risk == "medium"

    def test_phi_validation_report_findings_factory(self):
        report = PHIValidationReport()
        assert report.findings == []

    def test_disclaimer_result_selected_factory(self):
        dr = DisclaimerResult()
        assert dr.selected_disclaimers == []

    def test_compliance_report_checks_factory(self):
        report = ComplianceReport()
        assert report.checks == []

    def test_approval_result_reasons_factory(self):
        ar = ApprovalResult(decision=ApprovalDecision.APPROVED)
        assert ar.reasons == []
        assert ar.warnings == []

    def test_safety_state_claims_factory(self):
        state = SafetyState()
        assert state.claims == []
        assert state.config == {}

    def test_pipeline_result_steps_factory(self):
        state = SafetyState()
        pr = PipelineResult(state=state)
        assert pr.steps_completed == []
        assert pr.steps_skipped == []
        assert pr.errors == []

    def test_safety_service_result_warnings_factory(self):
        sr = SafetyServiceResult()
        assert sr.warnings == []
        assert sr.errors == []


class TestModelConfig:
    def test_from_attributes_on_all_response_schemas(self):
        for model in [
            HallucinationResult,
            HallucinationReport,
            UnsupportedClaim,
            UnsupportedClaimReport,
            ClinicalRiskResult,
            ClinicalRiskReport,
            EmergencyResult,
            EmergencyReport,
            PHIFinding,
            PHIValidationReport,
            DisclaimerConfig,
            DisclaimerResult,
            ComplianceCheck,
            ComplianceReport,
            ApprovalResult,
            SafetyState,
            PipelineResult,
            SafetyServiceResult,
        ]:
            config = model.model_config
            assert config.get("from_attributes") is True, f"{model.__name__} missing from_attributes"
