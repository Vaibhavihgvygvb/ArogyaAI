from app.ai.clinical_safety.config import ClinicalSafetyConfig


class TestClinicalSafetyConfig:
    def test_default_values(self):
        cfg = ClinicalSafetyConfig()
        assert cfg.CLINICAL_SAFETY_ENABLED is True
        assert cfg.CLINICAL_SAFETY_HALLUCINATION_THRESHOLD == 0.5
        assert cfg.CLINICAL_SAFETY_UNSUPPORTED_THRESHOLD == 0.4
        assert cfg.CLINICAL_SAFETY_RISK_LEVEL == "standard"
        assert cfg.CLINICAL_SAFETY_EMERGENCY_OVERRIDE is True
        assert cfg.CLINICAL_SAFETY_PHI_ENABLED is True
        assert cfg.CLINICAL_SAFETY_DISCLAIMER_REQUIRED is True
        assert cfg.CLINICAL_SAFETY_COMPLIANCE_ENABLED is True
        assert cfg.CLINICAL_SAFETY_APPROVAL_REQUIRED is True
        assert cfg.CLINICAL_SAFETY_MAX_CLAIMS == 100
        assert cfg.CLINICAL_SAFETY_MIN_EVIDENCE_SCORE == 0.3
        assert cfg.CLINICAL_SAFETY_PROHIBITED_TERMS == "guarantee,cure,100%,miracle,secret"

    def test_override_via_constructor(self):
        cfg = ClinicalSafetyConfig(
            CLINICAL_SAFETY_ENABLED=False,
            CLINICAL_SAFETY_HALLUCINATION_THRESHOLD=0.8,
            CLINICAL_SAFETY_UNSUPPORTED_THRESHOLD=0.7,
            CLINICAL_SAFETY_RISK_LEVEL="strict",
            CLINICAL_SAFETY_EMERGENCY_OVERRIDE=False,
            CLINICAL_SAFETY_PHI_ENABLED=False,
            CLINICAL_SAFETY_DISCLAIMER_REQUIRED=False,
            CLINICAL_SAFETY_COMPLIANCE_ENABLED=False,
            CLINICAL_SAFETY_APPROVAL_REQUIRED=False,
            CLINICAL_SAFETY_MAX_CLAIMS=200,
            CLINICAL_SAFETY_MIN_EVIDENCE_SCORE=0.6,
            CLINICAL_SAFETY_PROHIBITED_TERMS="cure,guarantee",
        )
        assert cfg.CLINICAL_SAFETY_ENABLED is False
        assert cfg.CLINICAL_SAFETY_HALLUCINATION_THRESHOLD == 0.8
        assert cfg.CLINICAL_SAFETY_UNSUPPORTED_THRESHOLD == 0.7
        assert cfg.CLINICAL_SAFETY_RISK_LEVEL == "strict"
        assert cfg.CLINICAL_SAFETY_EMERGENCY_OVERRIDE is False
        assert cfg.CLINICAL_SAFETY_PHI_ENABLED is False
        assert cfg.CLINICAL_SAFETY_DISCLAIMER_REQUIRED is False
        assert cfg.CLINICAL_SAFETY_COMPLIANCE_ENABLED is False
        assert cfg.CLINICAL_SAFETY_APPROVAL_REQUIRED is False
        assert cfg.CLINICAL_SAFETY_MAX_CLAIMS == 200
        assert cfg.CLINICAL_SAFETY_MIN_EVIDENCE_SCORE == 0.6
        assert cfg.CLINICAL_SAFETY_PROHIBITED_TERMS == "cure,guarantee"

    def test_type_correctness(self):
        cfg = ClinicalSafetyConfig()
        assert isinstance(cfg.CLINICAL_SAFETY_ENABLED, bool)
        assert isinstance(cfg.CLINICAL_SAFETY_HALLUCINATION_THRESHOLD, float)
        assert isinstance(cfg.CLINICAL_SAFETY_UNSUPPORTED_THRESHOLD, float)
        assert isinstance(cfg.CLINICAL_SAFETY_RISK_LEVEL, str)
        assert isinstance(cfg.CLINICAL_SAFETY_EMERGENCY_OVERRIDE, bool)
        assert isinstance(cfg.CLINICAL_SAFETY_PHI_ENABLED, bool)
        assert isinstance(cfg.CLINICAL_SAFETY_DISCLAIMER_REQUIRED, bool)
        assert isinstance(cfg.CLINICAL_SAFETY_COMPLIANCE_ENABLED, bool)
        assert isinstance(cfg.CLINICAL_SAFETY_APPROVAL_REQUIRED, bool)
        assert isinstance(cfg.CLINICAL_SAFETY_MAX_CLAIMS, int)
        assert isinstance(cfg.CLINICAL_SAFETY_MIN_EVIDENCE_SCORE, float)
        assert isinstance(cfg.CLINICAL_SAFETY_PROHIBITED_TERMS, str)

    def test_partial_override(self):
        cfg = ClinicalSafetyConfig(CLINICAL_SAFETY_ENABLED=False)
        assert cfg.CLINICAL_SAFETY_ENABLED is False
        assert cfg.CLINICAL_SAFETY_HALLUCINATION_THRESHOLD == 0.5
        assert cfg.CLINICAL_SAFETY_RISK_LEVEL == "standard"
        assert cfg.CLINICAL_SAFETY_MAX_CLAIMS == 100
