class ClinicalSafetyError(Exception):
    pass


class HallucinationDetectionError(ClinicalSafetyError):
    pass


class UnsupportedClaimError(ClinicalSafetyError):
    pass


class ClinicalRiskError(ClinicalSafetyError):
    pass


class EmergencyDetectionError(ClinicalSafetyError):
    pass


class PHIValidationError(ClinicalSafetyError):
    pass


class DisclaimerError(ClinicalSafetyError):
    pass


class ComplianceError(ClinicalSafetyError):
    pass


class SafetyApprovalError(ClinicalSafetyError):
    pass


class SafetyPipelineError(ClinicalSafetyError):
    pass


class SafetyConfigError(ClinicalSafetyError):
    pass


class SafetyValidationError(ClinicalSafetyError):
    pass
