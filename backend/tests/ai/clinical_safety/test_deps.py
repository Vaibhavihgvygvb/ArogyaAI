import pytest

from app.ai.clinical_safety.deps import (
    get_approval_engine,
    get_compliance_validator,
    get_disclaimer_engine,
    get_emergency_detector,
    get_hallucination_detector,
    get_phi_validator,
    get_pipeline,
    get_risk_engine,
    get_safety_service,
    get_unsupported_detector,
    reset_all,
    reset_approval_engine,
    reset_compliance_validator,
    reset_disclaimer_engine,
    reset_emergency_detector,
    reset_hallucination_detector,
    reset_phi_validator,
    reset_pipeline,
    reset_risk_engine,
    reset_safety_service,
    reset_unsupported_detector,
    set_approval_engine,
    set_compliance_validator,
    set_disclaimer_engine,
    set_emergency_detector,
    set_hallucination_detector,
    set_phi_validator,
    set_pipeline,
    set_risk_engine,
    set_safety_service,
    set_unsupported_detector,
)
from app.ai.clinical_safety.pipelines.pipeline import ClinicalSafetyPipeline
from app.ai.clinical_safety.services._service import ClinicalSafetyService
from app.ai.clinical_safety.services.approval import DefaultSafetyApprovalEngine
from app.ai.clinical_safety.services.compliance import DefaultComplianceValidator
from app.ai.clinical_safety.services.disclaimer import DefaultDisclaimerEngine
from app.ai.clinical_safety.services.emergency import DefaultEmergencyDetector
from app.ai.clinical_safety.services.hallucination import DefaultHallucinationDetector
from app.ai.clinical_safety.services.phi import DefaultPHIValidator
from app.ai.clinical_safety.services.risk import DefaultClinicalRiskEngine
from app.ai.clinical_safety.services.unsupported import DefaultUnsupportedClaimDetector


@pytest.fixture(autouse=True)
def cleanup():
    reset_all()
    yield
    reset_all()


class MockHallucinationDetector:
    async def detect(self, text, claims, evidence=None):
        from app.ai.clinical_safety.schemas import HallucinationReport
        return HallucinationReport()

    def _extract_claims(self, text):
        return []


class MockUnsupportedDetector:
    async def detect(self, claims, evidence=None):
        from app.ai.clinical_safety.schemas import UnsupportedClaimReport
        return UnsupportedClaimReport()


class MockRiskEngine:
    async def assess(self, hallucination_report, unsupported_report, emergency_report=None):
        from app.ai.clinical_safety.schemas import ClinicalRiskReport
        return ClinicalRiskReport()


class MockEmergencyDetector:
    async def detect(self, text, claims):
        from app.ai.clinical_safety.schemas import EmergencyReport
        return EmergencyReport()


class MockPHIValidator:
    async def validate(self, text):
        from app.ai.clinical_safety.schemas import PHIValidationReport
        return PHIValidationReport()


class MockDisclaimerEngine:
    async def select(self, risk_report, emergency_report, phi_report=None):
        from app.ai.clinical_safety.schemas import DisclaimerResult
        return DisclaimerResult()

    async def get_disclaimers(self):
        return []


class MockComplianceValidator:
    async def validate(self, hallucination_report, unsupported_report, disclaimer_result, risk_report=None):
        from app.ai.clinical_safety.schemas import ComplianceReport
        return ComplianceReport()


class MockApprovalEngine:
    async def approve(self, hallucination_report, unsupported_report, risk_report, compliance_report, disclaimer_result, emergency_report=None):
        from app.ai.clinical_safety.schemas import ApprovalResult, ApprovalDecision
        return ApprovalResult(decision=ApprovalDecision.APPROVED, reasons=["Mock approval."])


class TestClinicalSafetyDeps:
    def test_get_hallucination_detector_returns_default(self):
        instance = get_hallucination_detector()
        assert isinstance(instance, DefaultHallucinationDetector)

    def test_set_hallucination_detector_stores_custom(self):
        custom = MockHallucinationDetector()
        set_hallucination_detector(custom)
        assert get_hallucination_detector() is custom

    def test_reset_hallucination_detector_clears(self):
        set_hallucination_detector(MockHallucinationDetector())
        reset_hallucination_detector()
        assert isinstance(get_hallucination_detector(), DefaultHallucinationDetector)

    def test_hallucination_detector_singleton(self):
        a = get_hallucination_detector()
        b = get_hallucination_detector()
        assert a is b

    def test_get_unsupported_detector_returns_default(self):
        assert isinstance(get_unsupported_detector(), DefaultUnsupportedClaimDetector)

    def test_set_unsupported_detector_stores_custom(self):
        custom = MockUnsupportedDetector()
        set_unsupported_detector(custom)
        assert get_unsupported_detector() is custom

    def test_reset_unsupported_detector_clears(self):
        set_unsupported_detector(MockUnsupportedDetector())
        reset_unsupported_detector()
        assert isinstance(get_unsupported_detector(), DefaultUnsupportedClaimDetector)

    def test_get_risk_engine_returns_default(self):
        assert isinstance(get_risk_engine(), DefaultClinicalRiskEngine)

    def test_set_risk_engine_stores_custom(self):
        custom = MockRiskEngine()
        set_risk_engine(custom)
        assert get_risk_engine() is custom

    def test_reset_risk_engine_clears(self):
        set_risk_engine(MockRiskEngine())
        reset_risk_engine()
        assert isinstance(get_risk_engine(), DefaultClinicalRiskEngine)

    def test_get_emergency_detector_returns_default(self):
        assert isinstance(get_emergency_detector(), DefaultEmergencyDetector)

    def test_set_emergency_detector_stores_custom(self):
        custom = MockEmergencyDetector()
        set_emergency_detector(custom)
        assert get_emergency_detector() is custom

    def test_reset_emergency_detector_clears(self):
        set_emergency_detector(MockEmergencyDetector())
        reset_emergency_detector()
        assert isinstance(get_emergency_detector(), DefaultEmergencyDetector)

    def test_get_phi_validator_returns_default(self):
        assert isinstance(get_phi_validator(), DefaultPHIValidator)

    def test_set_phi_validator_stores_custom(self):
        custom = MockPHIValidator()
        set_phi_validator(custom)
        assert get_phi_validator() is custom

    def test_reset_phi_validator_clears(self):
        set_phi_validator(MockPHIValidator())
        reset_phi_validator()
        assert isinstance(get_phi_validator(), DefaultPHIValidator)

    def test_get_disclaimer_engine_returns_default(self):
        assert isinstance(get_disclaimer_engine(), DefaultDisclaimerEngine)

    def test_set_disclaimer_engine_stores_custom(self):
        custom = MockDisclaimerEngine()
        set_disclaimer_engine(custom)
        assert get_disclaimer_engine() is custom

    def test_reset_disclaimer_engine_clears(self):
        set_disclaimer_engine(MockDisclaimerEngine())
        reset_disclaimer_engine()
        assert isinstance(get_disclaimer_engine(), DefaultDisclaimerEngine)

    def test_get_compliance_validator_returns_default(self):
        assert isinstance(get_compliance_validator(), DefaultComplianceValidator)

    def test_set_compliance_validator_stores_custom(self):
        custom = MockComplianceValidator()
        set_compliance_validator(custom)
        assert get_compliance_validator() is custom

    def test_reset_compliance_validator_clears(self):
        set_compliance_validator(MockComplianceValidator())
        reset_compliance_validator()
        assert isinstance(get_compliance_validator(), DefaultComplianceValidator)

    def test_get_approval_engine_returns_default(self):
        assert isinstance(get_approval_engine(), DefaultSafetyApprovalEngine)

    def test_set_approval_engine_stores_custom(self):
        custom = MockApprovalEngine()
        set_approval_engine(custom)
        assert get_approval_engine() is custom

    def test_reset_approval_engine_clears(self):
        set_approval_engine(MockApprovalEngine())
        reset_approval_engine()
        assert isinstance(get_approval_engine(), DefaultSafetyApprovalEngine)

    def test_get_pipeline_returns_default(self):
        assert isinstance(get_pipeline(), ClinicalSafetyPipeline)

    def test_set_pipeline_stores_custom(self):
        custom = ClinicalSafetyPipeline()
        set_pipeline(custom)
        assert get_pipeline() is custom

    def test_reset_pipeline_clears(self):
        set_pipeline(ClinicalSafetyPipeline())
        reset_pipeline()
        assert isinstance(get_pipeline(), ClinicalSafetyPipeline)

    def test_get_safety_service_returns_default(self):
        assert isinstance(get_safety_service(), ClinicalSafetyService)

    def test_set_safety_service_stores_custom(self):
        custom = ClinicalSafetyService()
        set_safety_service(custom)
        assert get_safety_service() is custom

    def test_reset_safety_service_clears(self):
        set_safety_service(ClinicalSafetyService())
        reset_safety_service()
        assert isinstance(get_safety_service(), ClinicalSafetyService)

    def test_pipeline_singleton(self):
        a = get_pipeline()
        b = get_pipeline()
        assert a is b

    def test_service_singleton(self):
        a = get_safety_service()
        b = get_safety_service()
        assert a is b

    def test_reset_all_clears_everything(self):
        set_hallucination_detector(MockHallucinationDetector())
        set_unsupported_detector(MockUnsupportedDetector())
        set_risk_engine(MockRiskEngine())
        set_emergency_detector(MockEmergencyDetector())
        set_phi_validator(MockPHIValidator())
        set_disclaimer_engine(MockDisclaimerEngine())
        set_compliance_validator(MockComplianceValidator())
        set_approval_engine(MockApprovalEngine())
        set_pipeline(ClinicalSafetyPipeline())
        set_safety_service(ClinicalSafetyService())

        reset_all()

        assert isinstance(get_hallucination_detector(), DefaultHallucinationDetector)
        assert isinstance(get_unsupported_detector(), DefaultUnsupportedClaimDetector)
        assert isinstance(get_risk_engine(), DefaultClinicalRiskEngine)
        assert isinstance(get_emergency_detector(), DefaultEmergencyDetector)
        assert isinstance(get_phi_validator(), DefaultPHIValidator)
        assert isinstance(get_disclaimer_engine(), DefaultDisclaimerEngine)
        assert isinstance(get_compliance_validator(), DefaultComplianceValidator)
        assert isinstance(get_approval_engine(), DefaultSafetyApprovalEngine)
        assert isinstance(get_pipeline(), ClinicalSafetyPipeline)
        assert isinstance(get_safety_service(), ClinicalSafetyService)

    def test_set_custom_engine_affects_new_pipeline(self):
        custom = MockHallucinationDetector()
        set_hallucination_detector(custom)
        reset_pipeline()
        pipeline = get_pipeline()
        assert pipeline._hallucination_detector is custom

    def test_service_defaults_use_default_pipeline(self):
        service = get_safety_service()
        assert isinstance(service._pipeline, ClinicalSafetyPipeline)
