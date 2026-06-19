from app.ai.clinical_safety.services.hallucination import DefaultHallucinationDetector
from app.ai.clinical_safety.services.unsupported import DefaultUnsupportedClaimDetector
from app.ai.clinical_safety.services.risk import DefaultClinicalRiskEngine
from app.ai.clinical_safety.services.emergency import DefaultEmergencyDetector
from app.ai.clinical_safety.services.phi import DefaultPHIValidator
from app.ai.clinical_safety.services.disclaimer import DefaultDisclaimerEngine
from app.ai.clinical_safety.services.compliance import DefaultComplianceValidator
from app.ai.clinical_safety.services.approval import DefaultSafetyApprovalEngine
from app.ai.clinical_safety.pipelines.pipeline import ClinicalSafetyPipeline
from app.ai.clinical_safety.services._service import ClinicalSafetyService
from app.ai.clinical_safety.interfaces.hallucination import HallucinationDetector
from app.ai.clinical_safety.interfaces.unsupported import UnsupportedClaimDetector
from app.ai.clinical_safety.interfaces.risk import ClinicalRiskEngine
from app.ai.clinical_safety.interfaces.emergency import EmergencyDetector
from app.ai.clinical_safety.interfaces.phi import PHIValidator
from app.ai.clinical_safety.interfaces.disclaimer import DisclaimerEngine
from app.ai.clinical_safety.interfaces.compliance import ComplianceValidator
from app.ai.clinical_safety.interfaces.approval import SafetyApprovalEngine


_hallucination: HallucinationDetector | None = None
_unsupported: UnsupportedClaimDetector | None = None
_risk: ClinicalRiskEngine | None = None
_emergency: EmergencyDetector | None = None
_phi: PHIValidator | None = None
_disclaimer: DisclaimerEngine | None = None
_compliance: ComplianceValidator | None = None
_approval: SafetyApprovalEngine | None = None
_pipeline: ClinicalSafetyPipeline | None = None
_service: ClinicalSafetyService | None = None


def get_hallucination_detector() -> HallucinationDetector:
    global _hallucination
    if _hallucination is None:
        _hallucination = DefaultHallucinationDetector()
    return _hallucination


def set_hallucination_detector(d: HallucinationDetector) -> None:
    global _hallucination
    _hallucination = d


def reset_hallucination_detector() -> None:
    global _hallucination
    _hallucination = None


def get_unsupported_detector() -> UnsupportedClaimDetector:
    global _unsupported
    if _unsupported is None:
        _unsupported = DefaultUnsupportedClaimDetector()
    return _unsupported


def set_unsupported_detector(d: UnsupportedClaimDetector) -> None:
    global _unsupported
    _unsupported = d


def reset_unsupported_detector() -> None:
    global _unsupported
    _unsupported = None


def get_risk_engine() -> ClinicalRiskEngine:
    global _risk
    if _risk is None:
        _risk = DefaultClinicalRiskEngine()
    return _risk


def set_risk_engine(e: ClinicalRiskEngine) -> None:
    global _risk
    _risk = e


def reset_risk_engine() -> None:
    global _risk
    _risk = None


def get_emergency_detector() -> EmergencyDetector:
    global _emergency
    if _emergency is None:
        _emergency = DefaultEmergencyDetector()
    return _emergency


def set_emergency_detector(d: EmergencyDetector) -> None:
    global _emergency
    _emergency = d


def reset_emergency_detector() -> None:
    global _emergency
    _emergency = None


def get_phi_validator() -> PHIValidator:
    global _phi
    if _phi is None:
        _phi = DefaultPHIValidator()
    return _phi


def set_phi_validator(v: PHIValidator) -> None:
    global _phi
    _phi = v


def reset_phi_validator() -> None:
    global _phi
    _phi = None


def get_disclaimer_engine() -> DisclaimerEngine:
    global _disclaimer
    if _disclaimer is None:
        _disclaimer = DefaultDisclaimerEngine()
    return _disclaimer


def set_disclaimer_engine(e: DisclaimerEngine) -> None:
    global _disclaimer
    _disclaimer = e


def reset_disclaimer_engine() -> None:
    global _disclaimer
    _disclaimer = None


def get_compliance_validator() -> ComplianceValidator:
    global _compliance
    if _compliance is None:
        _compliance = DefaultComplianceValidator()
    return _compliance


def set_compliance_validator(v: ComplianceValidator) -> None:
    global _compliance
    _compliance = v


def reset_compliance_validator() -> None:
    global _compliance
    _compliance = None


def get_approval_engine() -> SafetyApprovalEngine:
    global _approval
    if _approval is None:
        _approval = DefaultSafetyApprovalEngine()
    return _approval


def set_approval_engine(e: SafetyApprovalEngine) -> None:
    global _approval
    _approval = e


def reset_approval_engine() -> None:
    global _approval
    _approval = None


def get_pipeline() -> ClinicalSafetyPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = ClinicalSafetyPipeline(
            hallucination_detector=get_hallucination_detector(),
            unsupported_detector=get_unsupported_detector(),
            risk_engine=get_risk_engine(),
            emergency_detector=get_emergency_detector(),
            phi_validator=get_phi_validator(),
            disclaimer_engine=get_disclaimer_engine(),
            compliance_validator=get_compliance_validator(),
            approval_engine=get_approval_engine(),
        )
    return _pipeline


def set_pipeline(p: ClinicalSafetyPipeline) -> None:
    global _pipeline
    _pipeline = p


def reset_pipeline() -> None:
    global _pipeline
    _pipeline = None


def get_safety_service() -> ClinicalSafetyService:
    global _service
    if _service is None:
        _service = ClinicalSafetyService(pipeline=get_pipeline())
    return _service


def set_safety_service(s: ClinicalSafetyService) -> None:
    global _service
    _service = s


def reset_safety_service() -> None:
    global _service
    _service = None


def reset_all() -> None:
    reset_hallucination_detector()
    reset_unsupported_detector()
    reset_risk_engine()
    reset_emergency_detector()
    reset_phi_validator()
    reset_disclaimer_engine()
    reset_compliance_validator()
    reset_approval_engine()
    reset_pipeline()
    reset_safety_service()
