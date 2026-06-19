import pytest

from app.ai.clinical_safety.exceptions import (
    ClinicalSafetyError,
    HallucinationDetectionError,
    UnsupportedClaimError,
    ClinicalRiskError,
    EmergencyDetectionError,
    PHIValidationError,
    DisclaimerError,
    ComplianceError,
    SafetyApprovalError,
    SafetyPipelineError,
    SafetyConfigError,
    SafetyValidationError,
)


class TestClinicalSafetyExceptions:
    def test_exception_hierarchy(self):
        assert issubclass(ClinicalSafetyError, Exception)
        assert issubclass(HallucinationDetectionError, ClinicalSafetyError)
        assert issubclass(UnsupportedClaimError, ClinicalSafetyError)
        assert issubclass(ClinicalRiskError, ClinicalSafetyError)
        assert issubclass(EmergencyDetectionError, ClinicalSafetyError)
        assert issubclass(PHIValidationError, ClinicalSafetyError)
        assert issubclass(DisclaimerError, ClinicalSafetyError)
        assert issubclass(ComplianceError, ClinicalSafetyError)
        assert issubclass(SafetyApprovalError, ClinicalSafetyError)
        assert issubclass(SafetyPipelineError, ClinicalSafetyError)
        assert issubclass(SafetyConfigError, ClinicalSafetyError)
        assert issubclass(SafetyValidationError, ClinicalSafetyError)

    def test_exceptions_can_be_raised_and_caught(self):
        for exc_cls in [
            HallucinationDetectionError,
            UnsupportedClaimError,
            ClinicalRiskError,
            EmergencyDetectionError,
            PHIValidationError,
            DisclaimerError,
            ComplianceError,
            SafetyApprovalError,
            SafetyPipelineError,
            SafetyConfigError,
            SafetyValidationError,
        ]:
            with pytest.raises(exc_cls):
                raise exc_cls("test error")

    def test_exception_messages(self):
        assert str(HallucinationDetectionError("hallucination detected")) == "hallucination detected"
        assert str(UnsupportedClaimError("unsupported claim")) == "unsupported claim"
        assert str(ClinicalRiskError("high risk")) == "high risk"
        assert str(EmergencyDetectionError("emergency detected")) == "emergency detected"
        assert str(PHIValidationError("phi found")) == "phi found"
        assert str(DisclaimerError("disclaimer missing")) == "disclaimer missing"
        assert str(ComplianceError("compliance failed")) == "compliance failed"
        assert str(SafetyApprovalError("approval rejected")) == "approval rejected"
        assert str(SafetyPipelineError("pipeline error")) == "pipeline error"
        assert str(SafetyConfigError("invalid config")) == "invalid config"
        assert str(SafetyValidationError("validation failed")) == "validation failed"

    def test_isinstance_checks(self):
        exc = ClinicalSafetyError("base")
        assert isinstance(exc, ClinicalSafetyError)
        assert isinstance(exc, Exception)

        for exc_cls in [
            HallucinationDetectionError,
            UnsupportedClaimError,
            ClinicalRiskError,
            EmergencyDetectionError,
            PHIValidationError,
            DisclaimerError,
            ComplianceError,
            SafetyApprovalError,
            SafetyPipelineError,
            SafetyConfigError,
            SafetyValidationError,
        ]:
            instance = exc_cls("test")
            assert isinstance(instance, ClinicalSafetyError)
            assert isinstance(instance, exc_cls)

    def test_clinical_safety_error_default_message(self):
        assert str(ClinicalSafetyError()) == ""
